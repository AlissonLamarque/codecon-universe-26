from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import time
import webbrowser
from typing import Iterable

import win32con
import win32gui


@dataclass
class RelaxLaunch:
    url: str
    pid: int | None
    browser_name: str | None


def _relax_profile_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AntiBurnoutRelaxProfile"
    return Path.cwd() / ".anti_burnout_relax_profile"


def _resolve_browser_executable() -> str | None:
    candidates: list[str] = []
    preferred_order = ("chrome.exe", "brave.exe", "firefox.exe", "msedge.exe")

    # PATH-discoverable binaries first.
    for name in preferred_order:
        found = shutil.which(name)
        if found:
            candidates.append(found)

    # Common install paths as fallback.
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    known_paths = [
        Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        Path(program_files_x86) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        Path(program_files) / "Mozilla Firefox" / "firefox.exe",
        Path(program_files_x86) / "Mozilla Firefox" / "firefox.exe",
        Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for p in known_paths:
        if p.exists():
            candidates.append(str(p))

    seen: set[str] = set()
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            return c
    return None


def _launch_dedicated_relax_window(url: str) -> RelaxLaunch:
    browser_exe = _resolve_browser_executable()
    if not browser_exe:
        webbrowser.open_new(url)
        return RelaxLaunch(url=url, pid=None, browser_name=None)

    exe_name = Path(browser_exe).name.lower()
    relax_profile = _relax_profile_dir()
    try:
        relax_profile.mkdir(parents=True, exist_ok=True)
    except Exception:
        relax_profile = Path.cwd()

    if exe_name in {"chrome.exe", "brave.exe", "msedge.exe"}:
        # Isolated profile + regular window is more reliable for YouTube playback.
        # App mode (`--app`) can get stuck in perpetual loading on some setups.
        args = [
            browser_exe,
            f"--user-data-dir={str(relax_profile)}",
            "--no-first-run",
            "--new-window",
            url,
        ]
    elif exe_name == "firefox.exe":
        args = [browser_exe, "-new-window", url]
    else:
        args = [browser_exe, url]

    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return RelaxLaunch(url=url, pid=proc.pid, browser_name=exe_name)
    except Exception:
        webbrowser.open_new(url)
        return RelaxLaunch(url=url, pid=None, browser_name=exe_name)


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


def focus_relax_window(hwnd: int, *, maximize: bool = True) -> bool:
    try:
        if not win32gui.IsWindow(hwnd):
            return False

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        if maximize:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        return True
    except Exception:
        try:
            if not win32gui.IsWindow(hwnd):
                return False
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            return True
        except Exception:
            return False


def close_window(hwnd: int) -> bool:
    try:
        if not win32gui.IsWindow(hwnd):
            return False
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False


def block_productive_window(hwnd: int, pid: int) -> None:
    # Intentionally non-destructive: keep the app alive and only minimize.
    _minimize_window(hwnd)


def open_relax_urls(urls: Iterable[str]) -> list[RelaxLaunch]:
    launches: list[RelaxLaunch] = []
    for url in urls:
        try:
            launches.append(_launch_dedicated_relax_window(url))
            # Small gap helps browser absorb sequential opens more consistently.
            time.sleep(0.12)
        except Exception:
            # Ignore failure and continue with next URL.
            pass
    return launches

