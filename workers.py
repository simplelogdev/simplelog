import contextlib
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime

from PyQt6.QtCore import QThread, pyqtSignal

import azure_utils
import cloudwatch
import gcp_utils
import vercel_utils

# ── Docker timestamp helper ──────────────────────────────────────────────────

def _parse_docker_ts(line: str) -> tuple[int, str]:
    """Parse docker --timestamps output: 'RFC3339 message text'.

    Returns (ts_ms, message). Falls back to current time if parsing fails.
    """
    parts = line.split(" ", 1)
    if len(parts) == 2:
        try:
            dt = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000), parts[1]
        except (ValueError, IndexError):
            pass
    return int(time.time() * 1000), line


def _read_last_n_lines(path: str, n: int) -> tuple[list[str], int]:
    """Read the last *n* lines of *path* without loading the whole file.

    Uses binary seeks so it's O(tail size), not O(file size).
    Returns *(lines, eof_byte_offset)* — the offset is used to resume tailing.
    """
    CHUNK = 1 << 14  # 16 KB per backwards step
    with open(path, "rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        if file_size == 0 or n == 0:
            return [], file_size

        buf = b""
        pos = file_size
        while pos > 0 and buf.count(b"\n") <= n:
            step = min(CHUNK, pos)
            pos -= step
            f.seek(pos)
            buf = f.read(step) + buf

    lines = buf.decode("utf-8", errors="replace").splitlines()
    result = lines[-n:] if len(lines) > n else lines
    return result, file_size


class TailWorker(QThread):
    new_lines    = pyqtSignal(list)  # [(ts_ms, message), ...]
    error        = pyqtSignal(str)
    status       = pyqtSignal(str)
    history_done = pyqtSignal(int)

    def __init__(self, client, log_group, log_stream, filter_pattern,
                 interval_s, lookback_s):
        super().__init__()
        self._client         = client
        self._log_group      = log_group
        self._log_stream     = log_stream
        self._filter_pattern = filter_pattern
        self._interval_ms    = int(interval_s * 1000)
        self._lookback_s     = lookback_s
        self._stop           = False

    def stop(self):
        self._stop = True

    def run(self):
        start_ms = int((time.time() - self._lookback_s) * 1000)
        self.status.emit("Loading history…")
        try:
            events = cloudwatch.fetch_events(
                self._client, self._log_group, self._log_stream or None,
                start_ms=start_ms,
                filter_pattern=self._filter_pattern,
                max_events=None,
            )
            self._last_ts = events[-1][0] + 1 if events else int(time.time() * 1000)
            if events:
                self.new_lines.emit(events)
            self.history_done.emit(len(events))
        except RuntimeError as e:
            self.error.emit(str(e))
            return

        while not self._stop:
            self.msleep(self._interval_ms)
            if self._stop:
                break
            try:
                events = cloudwatch.fetch_events(
                    self._client, self._log_group, self._log_stream or None,
                    start_ms=self._last_ts,
                    filter_pattern=self._filter_pattern,
                    max_events=500,
                )
                if events:
                    self._last_ts = events[-1][0] + 1
                    self.new_lines.emit(events)
                    self.status.emit(f"Updated  —  {len(events)} new events")
                else:
                    self.status.emit("Tailing…  no new events")
            except RuntimeError as e:
                self.error.emit(str(e))


class FileWorker(QThread):
    new_lines = pyqtSignal(list)  # [(ts_ms, message), ...]
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self, path, tail_lines=100, interval_ms=200):
        super().__init__()
        self._path        = path
        self._tail_lines  = tail_lines
        self._interval_ms = interval_ms
        self._stop        = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self.status.emit(f"Loading {self._path}…")
            lines, eof_pos = _read_last_n_lines(self._path, self._tail_lines)
            if lines:
                now = int(time.time() * 1000)
                self.new_lines.emit([(now, line) for line in lines if line])
            self.status.emit(f"Tailing {self._path}")

            # Resume tailing from EOF — only new bytes are read from here on
            with open(self._path, "rb") as f:
                f.seek(eof_pos)
                while not self._stop:
                    raw = f.read()
                    if raw:
                        now = int(time.time() * 1000)
                        events = [
                            (now, line)
                            for line in raw.decode("utf-8", errors="replace").splitlines()
                            if line
                        ]
                        if events:
                            self.new_lines.emit(events)
                    else:
                        self.msleep(self._interval_ms)
        except OSError as e:
            self.error.emit(str(e))


class StdinWorker(QThread):
    new_lines = pyqtSignal(list)  # [(ts_ms, message), ...]
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        self.status.emit("Reading stdin…")
        try:
            for raw_line in sys.stdin:
                if self._stop:
                    break
                line = raw_line.rstrip()
                if line:
                    ts = int(time.time() * 1000)
                    self.new_lines.emit([(ts, line)])
            self.status.emit("stdin — stream closed")
        except Exception as e:
            self.error.emit(str(e))


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


class UpdateWorker(QThread):
    """Checks GitHub releases for a newer version."""
    update_available = pyqtSignal(str, str)  # (latest_tag, html_url)
    up_to_date       = pyqtSignal(str)       # (current_version)
    error            = pyqtSignal(str)

    _API = "https://api.github.com/repos/sindus/simplelog/releases/latest"

    def __init__(self, current_version: str):
        super().__init__()
        self._current = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                self._API,
                headers={"User-Agent": f"SimpleLog/{self._current}"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            latest = data.get("tag_name", "")
            if latest and _version_tuple(latest) > _version_tuple(self._current):
                self.update_available.emit(latest, data.get("html_url", ""))
            else:
                self.up_to_date.emit(self._current)
        except Exception as exc:
            self.error.emit(str(exc))


class DownloadWorker(QThread):
    """Downloads a file from a URL, emitting progress as it goes."""
    progress = pyqtSignal(int)   # 0-100
    finished = pyqtSignal(str)   # destination path
    error    = pyqtSignal(str)

    def __init__(self, url: str, dest: str, current_version: str):
        super().__init__()
        self._url = url
        self._dest = dest
        self._current = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": f"SimpleLog/{self._current}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(self._dest, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.emit(int(downloaded * 100 / total))
            self.progress.emit(100)
            self.finished.emit(self._dest)
        except Exception as exc:
            with contextlib.suppress(OSError):
                os.unlink(self._dest)
            self.error.emit(str(exc))


# ── SSH worker ────────────────────────────────────────────────────────────────

class SSHWorker(QThread):
    new_lines = pyqtSignal(list)   # [(ts_ms, message), ...]
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self, client, remote_path: str, tail_lines: int = 100) -> None:
        super().__init__()
        self._client      = client
        self._remote_path = remote_path
        self._tail_lines  = tail_lines
        self._stop        = False
        self._channel     = None

    def stop(self) -> None:
        self._stop = True
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass

    def run(self) -> None:
        self.status.emit(f"Connecting to {self._remote_path}…")
        try:
            cmd = f"tail -n {self._tail_lines} -f {shlex.quote(self._remote_path)}"
            _, stdout, stderr = self._client.exec_command(cmd, get_pty=False)
            self._channel = stdout.channel
            self.status.emit(f"Tailing {self._remote_path}")
            for raw_line in stdout:
                if self._stop or self._channel.closed:
                    break
                line = raw_line.rstrip("\n\r")
                if line:
                    ts = int(time.time() * 1000)
                    self.new_lines.emit([(ts, line)])
            if not self._stop:
                err = stderr.read().decode("utf-8", errors="replace").strip()
                if err:
                    self.error.emit(err)
                else:
                    self.status.emit("SSH stream ended")
        except Exception as e:
            if not self._stop:
                self.error.emit(str(e))
        finally:
            try:
                self._client.close()
            except Exception:
                pass


# ── Docker container worker ───────────────────────────────────────────────────

class DockerContainerWorker(QThread):
    new_lines = pyqtSignal(list)
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self, container_id: str, tail_lines: int = 100) -> None:
        super().__init__()
        self._container_id = container_id
        self._tail_lines   = tail_lines
        self._stop         = False
        self._proc         = None

    def stop(self) -> None:
        self._stop = True
        if self._proc:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def run(self) -> None:
        short = self._container_id[:12]
        self.status.emit(f"Streaming docker logs for {short}…")
        try:
            self._proc = subprocess.Popen(
                ["docker", "logs", "-f", "--timestamps",
                 f"--tail={self._tail_lines}", self._container_id],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                if self._stop:
                    break
                line = line.rstrip()
                if line:
                    ts, msg = _parse_docker_ts(line)
                    self.new_lines.emit([(ts, msg)])
            self._proc.wait()
            if not self._stop and self._proc.returncode not in (0, -15):
                self.error.emit(f"docker logs exited with code {self._proc.returncode}")
            elif not self._stop:
                self.status.emit("Docker log stream ended")
        except Exception as e:
            if not self._stop:
                self.error.emit(str(e))


# ── Docker Compose worker ─────────────────────────────────────────────────────

class DockerComposeWorker(QThread):
    new_lines = pyqtSignal(list)
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self, project_name: str, tail_lines: int = 100) -> None:
        super().__init__()
        self._project    = project_name
        self._tail_lines = tail_lines
        self._stop       = False
        self._proc       = None

    def stop(self) -> None:
        self._stop = True
        if self._proc:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def run(self) -> None:
        self.status.emit(f"Streaming compose stack {self._project}…")
        try:
            self._proc = subprocess.Popen(
                ["docker", "compose", "-p", self._project,
                 "logs", "-f", "--timestamps", f"--tail={self._tail_lines}"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                if self._stop:
                    break
                line = line.rstrip()
                if line:
                    ts, msg = _parse_docker_ts(line)
                    self.new_lines.emit([(ts, msg)])
            self._proc.wait()
            if not self._stop and self._proc.returncode not in (0, -15):
                self.error.emit(f"docker compose logs exited {self._proc.returncode}")
            elif not self._stop:
                self.status.emit("Compose log stream ended")
        except Exception as e:
            if not self._stop:
                self.error.emit(str(e))


# ── Docker exec file worker ───────────────────────────────────────────────────

class DockerExecFileWorker(QThread):
    new_lines = pyqtSignal(list)
    status    = pyqtSignal(str)
    error     = pyqtSignal(str)

    def __init__(self, container_id: str, remote_path: str, tail_lines: int = 100) -> None:
        super().__init__()
        self._container_id = container_id
        self._remote_path  = remote_path
        self._tail_lines   = tail_lines
        self._stop         = False
        self._proc         = None

    def stop(self) -> None:
        self._stop = True
        if self._proc:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def run(self) -> None:
        short = self._container_id[:12]
        self.status.emit(f"Tailing {self._remote_path} in {short}…")
        try:
            self._proc = subprocess.Popen(
                ["docker", "exec", self._container_id,
                 "tail", f"-n{self._tail_lines}", "-f", self._remote_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                if self._stop:
                    break
                line = line.rstrip()
                if line:
                    ts = int(time.time() * 1000)
                    self.new_lines.emit([(ts, line)])
            self._proc.wait()
            if not self._stop and self._proc.returncode not in (0, -15):
                self.error.emit(f"docker exec exited with code {self._proc.returncode}")
            elif not self._stop:
                self.status.emit("Container file stream ended")
        except Exception as e:
            if not self._stop:
                self.error.emit(str(e))


# ── Vercel worker ─────────────────────────────────────────────────────────────

class VercelWorker(QThread):
    """Polls Vercel deployment events and emits new log lines."""
    new_lines    = pyqtSignal(list)  # [(ts_ms, message), ...]
    status       = pyqtSignal(str)
    error        = pyqtSignal(str)
    history_done = pyqtSignal(int)

    def __init__(self, token: str, project_id: str, project_name: str,
                 deployment_id: str, interval_s: float = 3.0) -> None:
        super().__init__()
        self._token         = token
        self._project_id    = project_id
        self._project_name  = project_name
        self._deployment_id = deployment_id
        self._interval_ms   = int(interval_s * 1000)
        self._stop          = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        self.status.emit(f"Loading logs for {self._project_name}…")
        try:
            events = vercel_utils.fetch_deployment_events(self._token, self._deployment_id)
            self._last_ts = events[-1][0] + 1 if events else int(time.time() * 1000)
            if events:
                self.new_lines.emit(events)
            self.history_done.emit(len(events))
            self.status.emit(f"Tailing {self._project_name} — {len(events)} events loaded")
        except RuntimeError as e:
            self.error.emit(str(e))
            return

        while not self._stop:
            self.msleep(self._interval_ms)
            if self._stop:
                break
            try:
                events = vercel_utils.fetch_deployment_events(
                    self._token, self._deployment_id, since_ms=self._last_ts
                )
                if events:
                    self._last_ts = events[-1][0] + 1
                    self.new_lines.emit(events)
                    self.status.emit(f"{self._project_name} — {len(events)} new events")
                else:
                    self.status.emit(f"Tailing {self._project_name}…")
            except RuntimeError as e:
                self.error.emit(str(e))


# ── GCP Cloud Logging worker ──────────────────────────────────────────────────

class GCPWorker(QThread):
    """Polls Google Cloud Logging and emits new log entries."""
    new_lines    = pyqtSignal(list)  # [(ts_ms, message), ...]
    status       = pyqtSignal(str)
    error        = pyqtSignal(str)
    history_done = pyqtSignal(int)

    def __init__(self, client, project_id: str, resource_type: str,
                 severity: str, custom_filter: str,
                 lookback_hours: float = 1.0, interval_s: float = 5.0) -> None:
        super().__init__()
        self._client        = client
        self._project_id    = project_id
        self._resource_type = resource_type
        self._severity      = severity
        self._custom        = custom_filter
        self._lookback_h    = lookback_hours
        self._interval_ms   = int(interval_s * 1000)
        self._stop          = False

    def stop(self) -> None:
        self._stop = True

    def _make_filter(self, since: datetime | None) -> str:
        return gcp_utils.build_filter(
            resource_type=self._resource_type,
            severity=self._severity,
            custom=self._custom,
            since=since,
        )

    def run(self) -> None:
        self.status.emit(f"Loading GCP logs for {self._project_id}…")
        since = datetime.now(UTC) - __import__("datetime").timedelta(hours=self._lookback_h)
        try:
            events = gcp_utils.fetch_entries(self._client, self._make_filter(since))
            self._last_ts = (
                datetime.fromtimestamp(events[-1][0] / 1000, tz=UTC)
                if events else datetime.now(UTC)
            )
            if events:
                self.new_lines.emit(events)
            self.history_done.emit(len(events))
            self.status.emit(f"GCP {self._project_id} — {len(events)} entries loaded")
        except RuntimeError as e:
            self.error.emit(str(e))
            return

        while not self._stop:
            self.msleep(self._interval_ms)
            if self._stop:
                break
            try:
                events = gcp_utils.fetch_entries(
                    self._client,
                    self._make_filter(self._last_ts),
                    max_results=200,
                )
                if events:
                    self._last_ts = datetime.fromtimestamp(events[-1][0] / 1000, tz=UTC)
                    self.new_lines.emit(events)
                    self.status.emit(f"GCP {self._project_id} — {len(events)} new entries")
                else:
                    self.status.emit(f"GCP {self._project_id} — tailing…")
            except RuntimeError as e:
                self.error.emit(str(e))


# ── Azure Monitor worker ──────────────────────────────────────────────────────

class AzureWorker(QThread):
    """Polls Azure Monitor Log Analytics and emits new log rows."""
    new_lines    = pyqtSignal(list)  # [(ts_ms, message), ...]
    status       = pyqtSignal(str)
    error        = pyqtSignal(str)
    history_done = pyqtSignal(int)

    def __init__(self, logs_client, workspace_id: str, query: str,
                 label: str = "", timespan_hours: float = 1.0,
                 interval_s: float = 10.0) -> None:
        super().__init__()
        self._client       = logs_client
        self._workspace_id = workspace_id
        self._query        = query
        self._label        = label or workspace_id[:8]
        self._timespan_h   = timespan_hours
        self._interval_ms  = int(interval_s * 1000)
        self._stop         = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        self.status.emit(f"Loading Azure logs — {self._label}…")
        try:
            events = azure_utils.fetch_logs(
                self._client, self._workspace_id,
                self._query, self._timespan_h,
            )
            self._last_dt = (
                datetime.fromtimestamp(events[-1][0] / 1000, tz=UTC)
                if events else datetime.now(UTC)
            )
            if events:
                self.new_lines.emit(events)
            self.history_done.emit(len(events))
            self.status.emit(f"Azure {self._label} — {len(events)} rows loaded")
        except RuntimeError as e:
            self.error.emit(str(e))
            return

        while not self._stop:
            self.msleep(self._interval_ms)
            if self._stop:
                break
            try:
                events = azure_utils.fetch_logs_since(
                    self._client, self._workspace_id,
                    self._query, self._last_dt,
                )
                if events:
                    self._last_dt = datetime.fromtimestamp(events[-1][0] / 1000, tz=UTC)
                    self.new_lines.emit(events)
                    self.status.emit(f"Azure {self._label} — {len(events)} new rows")
                else:
                    self.status.emit(f"Azure {self._label} — tailing…")
            except RuntimeError as e:
                self.error.emit(str(e))
