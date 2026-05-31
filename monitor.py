from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import psutil
import win32gui
import win32process


@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    process_name: str
    title: str


def _window_info_from_hwnd(hwnd: int) -> Optional[WindowInfo]:
    if not hwnd or not win32gui.IsWindow(hwnd):
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


def get_active_window_info() -> Optional[WindowInfo]:
    hwnd = win32gui.GetForegroundWindow()
    return _window_info_from_hwnd(hwnd)


def get_window_info(hwnd: int) -> Optional[WindowInfo]:
    return _window_info_from_hwnd(hwnd)


def list_top_windows(
    predicate: Optional[Callable[[WindowInfo], bool]] = None,
    *,
    visible_only: bool = True,
) -> list[WindowInfo]:
    windows: list[WindowInfo] = []

    def _cb(hwnd: int, _: int) -> bool:
        try:
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return True
            info = _window_info_from_hwnd(hwnd)
            if not info:
                return True
            if predicate and not predicate(info):
                return True
            windows.append(info)
        except Exception:
            return True
        return True

    win32gui.EnumWindows(_cb, 0)
    return windows


def find_windows_by_pid(pid: int) -> list[WindowInfo]:
    # Include minimized windows, so we can restore previously-opened relax windows.
    return list_top_windows(predicate=lambda w: w.pid == pid, visible_only=False)


