#!/usr/bin/env python3
"""
SimpleLog — multi-source log viewer
Usage:
  simplelog                              → CloudWatch GUI
  simplelog /path/to/file.log           → tail file(s) in tabs
  command | simplelog                   → read piped stdin
  simplelog --split vertical f1 f2      → open f1 & f2 side by side
  simplelog --split horizontal f1 f2    → open f1 & f2 top/bottom
"""
import argparse
import json
import os
import stat
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

import i18n
from ui import MainWindow
from ui import apply_style as apply_dark_palette
from version import __version__  # noqa: F401  (imported for UpdateWorker)

# Unique socket name for this app's IPC channel
_SOCKET_NAME = "simplelog-ipc-v1"


def _parse_args():
    parser = argparse.ArgumentParser(
        prog="simplelog",
        description="SimpleLog — multi-source log viewer",
        add_help=False,
    )
    parser.add_argument(
        "--split",
        choices=["tab", "vertical", "horizontal"],
        default="tab",
        metavar="MODE",
        help="How to open logs: tab (default), vertical (side by side), horizontal (top/bottom)",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=100,
        metavar="N",
        help="Number of lines to load from the end of each file (default: 100)",
    )
    parser.add_argument("files", nargs="*", help="Log file paths to open")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args, _ = parser.parse_known_args()
    return args


def _stdin_is_piped() -> bool:
    """Return True only when stdin is an actual pipe/FIFO (e.g. `cmd | simplelog`)."""
    try:
        return stat.S_ISFIFO(os.fstat(sys.stdin.fileno()).st_mode)
    except Exception:
        return False


def _try_forward_to_existing(args) -> bool:
    """
    If another SimpleLog instance is already running, send our args to it and
    return True (caller should exit).  Returns False if no instance found.
    """
    # stdin piping cannot be forwarded — always start a new instance
    if _stdin_is_piped():
        return False

    socket = QLocalSocket()
    socket.connectToServer(_SOCKET_NAME)
    if not socket.waitForConnected(300):
        return False

    payload = json.dumps({
        "files": args.files,
        "split": args.split,
        "tail": args.tail,
    }).encode() + b"\n"
    socket.write(payload)
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    return True


def _setup_ipc_server(window: MainWindow) -> QLocalServer:
    """Start the local IPC server so this instance can receive args from future invocations."""
    QLocalServer.removeServer(_SOCKET_NAME)  # clean up stale socket from a previous crash
    server = QLocalServer(window)
    server.listen(_SOCKET_NAME)

    def _on_connection():
        conn = server.nextPendingConnection()
        # Use a closure to accumulate data (readyRead may fire multiple times)
        buf = bytearray()

        def _on_data():
            buf.extend(bytes(conn.readAll()))
            if b"\n" not in buf:
                return
            try:
                msg = json.loads(buf.split(b"\n")[0])
            except (ValueError, KeyError):
                return
            for path in msg.get("files", []):
                if os.path.isfile(path):
                    window.open_file_tab(path, msg.get("tail", 100), msg.get("split", "tab"))
            # Bring window to front
            window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
            window.raise_()
            window.activateWindow()

        conn.readyRead.connect(_on_data)

    server.newConnection.connect(_on_connection)
    return server


def main():
    args = _parse_args()

    # Need a QApplication to use QLocalSocket (even before showing a window)
    app = QApplication(sys.argv)
    app.setApplicationName("SimpleLog")
    app.setStyle("Fusion")
    apply_dark_palette(app)

    # ── Single-instance check ──────────────────────────────────────────────────
    if _try_forward_to_existing(args):
        # Another instance accepted our request — nothing more to do.
        sys.exit(0)

    # ── First (primary) instance ───────────────────────────────────────────────
    i18n.load_locale()
    window = MainWindow()
    window.show()

    # Start listening for future invocations
    _ipc_server = _setup_ipc_server(window)  # noqa: F841 — keep reference alive

    stdin_is_pipe = _stdin_is_piped()

    def _open_initial_tabs():
        if stdin_is_pipe:
            window.open_stdin_tab()
        for path in args.files:
            if os.path.isfile(path):
                window.open_file_tab(path, args.tail, args.split)
            else:
                QMessageBox.warning(
                    window,
                    i18n.tr("err_file_not_found"),
                    i18n.tr("err_cannot_open", path=path),
                )

    QTimer.singleShot(100, _open_initial_tabs)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
