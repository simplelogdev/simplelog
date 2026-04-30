"""ssh_utils.py — SSH connection helpers for SimpleLog."""
from __future__ import annotations

import shlex

import paramiko


def make_client(
    host: str,
    user: str,
    port: int = 22,
    key_path: str | None = None,
    password: str | None = None,
    timeout: float = 10.0,
) -> paramiko.SSHClient:
    """Open and return an authenticated SSHClient.

    Tries key_path first (if given), then SSH agent / ~/.ssh/id_*, then password.
    Raises RuntimeError with a human-readable message on any failure.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            port=port,
            username=user,
            key_filename=key_path or None,
            password=password or None,
            timeout=timeout,
            look_for_keys=True,
            allow_agent=True,
        )
    except paramiko.AuthenticationException as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except paramiko.SSHException as e:
        raise RuntimeError(f"SSH error: {e}") from e
    except OSError as e:
        raise RuntimeError(f"Connection failed: {e}") from e
    return client


def list_remote_dir(client: paramiko.SSHClient, path: str) -> list[str]:
    """Return sorted filenames in *path* on the remote host via SFTP.

    Raises RuntimeError if the path cannot be listed.
    """
    try:
        sftp = client.open_sftp()
        try:
            attrs = sftp.listdir_attr(path)
        finally:
            sftp.close()
    except Exception as e:
        raise RuntimeError(f"Cannot list {path}: {e}") from e
    return sorted(a.filename for a in attrs)


def list_remote_dir_full(client: paramiko.SSHClient, path: str) -> list[tuple[str, bool]]:
    """Return list of (name, is_dir) sorted by name for *path* on the remote host.

    Raises RuntimeError if the path cannot be listed.
    """
    import stat as stat_mod
    try:
        sftp = client.open_sftp()
        try:
            attrs = sftp.listdir_attr(path)
        finally:
            sftp.close()
    except Exception as e:
        raise RuntimeError(f"Cannot list {path}: {e}") from e
    result = []
    for a in sorted(attrs, key=lambda x: x.filename):
        is_dir = stat_mod.S_ISDIR(a.st_mode) if a.st_mode else False
        result.append((a.filename, is_dir))
    return result


def test_file_readable(client: paramiko.SSHClient, path: str) -> bool:
    """Return True if *path* exists and is a regular file on the remote host."""
    _, stdout, _ = client.exec_command(f"test -f {shlex.quote(path)} && echo yes || echo no")
    return stdout.read().strip() == b"yes"
