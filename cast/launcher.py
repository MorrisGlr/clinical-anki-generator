"""Entry point for the PyInstaller-packaged CAST desktop app.

This module is only used when CAST is distributed as a standalone .app or .exe.
It is not part of the normal `cast` CLI or `pip install` workflow.

On launch it:
  1. Creates ~/Documents/CAST/{html_dump,gen_anki}/ if they do not exist.
  2. Sets CAST_DATA_DIR so core.py, cli.py, and server/app.py all resolve
     paths to the same user-writable location.
  3. Finds a free port in the range 7070-7072.
  4. Starts the Flask server in a daemon thread.
  5. Waits until the server responds, then opens the default browser.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _data_dir() -> Path:
    return Path.home() / "Documents" / "CAST"


def _find_free_port(start: int = 7070, end: int = 7072) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise OSError(f"No free port found in range {start}–{end}.")


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def main() -> None:
    data = _data_dir()
    data.mkdir(parents=True, exist_ok=True)
    (data / "html_dump").mkdir(exist_ok=True)
    (data / "gen_anki").mkdir(exist_ok=True)

    os.environ["CAST_DATA_DIR"] = str(data)

    port = _find_free_port()
    url = f"http://localhost:{port}"

    from cast.server.app import create_app

    app = create_app()

    server_thread = threading.Thread(
        target=lambda: app.run(port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    if _wait_for_server(port):
        webbrowser.open(url)
    else:
        print(f"CAST server did not start in time. Open {url} manually.")

    server_thread.join()


if __name__ == "__main__":
    main()
