from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psutil
import win32gui
import win32process


@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    process_name: str
    title: str


def get_active_window_info() -> Optional[WindowInfo]:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None

    title = win32gui.GetWindowText(hwnd) or ""
    _, pid = win32process.GetWindowThreadProcessId(hwnd)

    try:
        process_name = psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

    return WindowInfo(
        hwnd=hwnd,
        pid=pid,
        process_name=process_name,
        title=title,
    )

