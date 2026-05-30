from __future__ import annotations

import time
import webbrowser
from typing import Iterable

import win32con
import win32gui


def _minimize_window(hwnd: int) -> bool:
    try:
        if not win32gui.IsWindow(hwnd):
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_FORCEMINIMIZE)
        return True
    except Exception:
        # Fallback to regular minimize if force minimize fails.
        try:
            if not win32gui.IsWindow(hwnd):
                return False
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            return False


def block_productive_window(hwnd: int, pid: int) -> None:
    # Intentionally non-destructive: keep the app alive and only minimize.
    _minimize_window(hwnd)


def open_relax_urls(urls: Iterable[str]) -> None:
    for url in urls:
        try:
            webbrowser.open_new_tab(url)
            # Small gap helps browser absorb sequential opens more consistently.
            time.sleep(0.12)
        except Exception:
            # Ignore failure and continue with next URL.
            pass

