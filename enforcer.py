from __future__ import annotations

import time
import webbrowser
from typing import Iterable

import psutil
import win32con
import win32gui


def close_window_gracefully(hwnd: int) -> bool:
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False


def kill_process(pid: int) -> bool:
    try:
        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except Exception:
            process.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def block_productive_window(hwnd: int, pid: int) -> None:
    close_window_gracefully(hwnd)
    time.sleep(0.2)
    kill_process(pid)


def open_relax_urls(urls: Iterable[str]) -> None:
    for url in urls:
        try:
            webbrowser.open_new_tab(url)
            time.sleep(0.15)
        except Exception:
            # Ignore failure and continue with next URL.
            pass

