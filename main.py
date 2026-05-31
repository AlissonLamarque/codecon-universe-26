from __future__ import annotations

import argparse
import threading
import time
from typing import Callable

from alert_agent import AlertContext, build_alert_message
from app_state import AppState
from config import (
    BLOCK_COOLDOWN_SECONDS,
    DEV_MODE,
    ENABLE_OVERLAY,
    MEDIA_COOLDOWN_SECONDS,
    PANIC_COOLDOWN_SECONDS,
    POLL_INTERVAL_SECONDS,
    PRE_BLOCK_POPUP_SECONDS,
    RELAX_BROWSER_PROCESSES,
    RELAX_ESCAPE_COOLDOWN_SECONDS,
    RELAX_MAX_SIMULTANEOUS_VIDEOS,
    RELAX_QUERIES,
    RELAX_TITLE_KEYWORDS,
)
from enforcer import block_productive_window, focus_relax_window, open_relax_urls
from launcher import show_launcher
from logger_utils import log_event
from monitor import find_windows_by_pid, get_active_window_info, get_window_info
from overlay import show_intervention_popup
from policy import is_panic_target, should_block
from state_machine import CycleState, REST_FORCED
from tray_app import build_tray
from youtube_resolver import YouTubeResolver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Anti-Burnout app")
    parser.add_argument(
        "--launcher",
        action="store_true",
        help="Force startup launcher UI.",
    )
    parser.add_argument(
        "--no-launcher",
        action="store_true",
        help="Skip launcher UI and start immediately.",
    )
    parser.add_argument(
        "--profile",
        choices=["dev", "live", "panic"],
        help="Startup profile when skipping launcher.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Disable dev safety allowlist (blocks IDE/shell apps too).",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Force dev mode on.",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Disable alert notifications (legacy name).",
    )
    parser.add_argument(
        "--no-notifications",
        action="store_true",
        dest="no_overlay",
        help="Disable alert notifications.",
    )
    return parser.parse_args()


def resolve_startup_state(args: argparse.Namespace) -> AppState | None:
    def _from_launcher() -> AppState | None:
        launch = show_launcher(
            default_dev_mode=DEV_MODE,
            default_panic_mode=False,
            default_overlay_enabled=ENABLE_OVERLAY,
            default_enabled=True,
        )
        if launch is None:
            return None
        return AppState(
            enabled=launch.enabled,
            dev_mode=launch.dev_mode,
            panic_mode=launch.panic_mode,
            overlay_enabled=launch.overlay_enabled,
        )

    # Explicit launcher has highest priority.
    if args.launcher and not args.no_launcher:
        return _from_launcher()

    # CLI explicit profile has top priority.
    if args.profile == "dev":
        return AppState(
            dev_mode=True,
            panic_mode=False,
            enabled=True,
            overlay_enabled=ENABLE_OVERLAY and not args.no_overlay,
        )
    if args.profile == "live":
        return AppState(
            dev_mode=False,
            panic_mode=False,
            enabled=True,
            overlay_enabled=ENABLE_OVERLAY and not args.no_overlay,
        )
    if args.profile == "panic":
        return AppState(
            dev_mode=False,
            panic_mode=True,
            enabled=True,
            overlay_enabled=ENABLE_OVERLAY and not args.no_overlay,
        )

    # Backward compatibility CLI flags.
    if args.live or args.dev or args.no_overlay or args.no_launcher:
        if args.live:
            dev_mode = False
        elif args.dev:
            dev_mode = True
        else:
            dev_mode = DEV_MODE

        overlay_enabled = ENABLE_OVERLAY and not args.no_overlay
        return AppState(dev_mode=dev_mode, overlay_enabled=overlay_enabled)

    # Default behavior: one-click launcher UI.
    return _from_launcher()


def monitor_loop(
    state: AppState,
    request_menu_refresh,
    send_notification: Callable[[str, str], None],
) -> None:
    resolver = YouTubeResolver()
    cycle = CycleState()
    relax_window_hwnds: set[int] = set()
    relax_window_pids: set[int] = set()
    relax_primary_hwnd: int | None = None
    relax_session_active = False
    relax_browser_processes = {name.lower() for name in RELAX_BROWSER_PROCESSES}
    relax_title_keywords = tuple(keyword.lower() for keyword in RELAX_TITLE_KEYWORDS)
    ignored_browser_titles = {"default ime", "msctfime ui"}

    def _media_hint(media_level: int) -> str:
        if not RELAX_QUERIES:
            return "conteudo relaxante"
        return RELAX_QUERIES[media_level % len(RELAX_QUERIES)]

    def _alert_message(
        event: str,
        media_level: int,
        *,
        process_name: str | None = None,
        attempt_count: int = 0,
    ) -> str:
        snap = state.snapshot()
        return build_alert_message(
            AlertContext(
                event=event,
                phase=cycle.phase,
                cycle_index=cycle.cycle_index,
                process_name=process_name,
                media_hint=_media_hint(media_level),
                panic_mode=snap["panic_mode"],
                work_seconds=cycle.current_work_seconds(),
                rest_seconds=cycle.current_rest_seconds(),
                attempt_count=attempt_count,
                autocratic=attempt_count >= 2,
            )
        )

    def _show_agent_message(reason: str, message: str) -> bool:
        current = state.snapshot()
        if not current["enabled"] or not current["overlay_enabled"]:
            return False

        send_notification("Anti-Burnout", message)
        log_event("ALERT_SHOWN", reason=reason, message=message)
        return True

    def _show_pre_block_popup(reason: str, message: str) -> bool:
        current = state.snapshot()
        if not current["enabled"] or not current["overlay_enabled"]:
            return False
        try:
            show_intervention_popup(message, duration_seconds=PRE_BLOCK_POPUP_SECONDS)
            log_event(
                "PRE_BLOCK_POPUP_SHOWN",
                reason=reason,
                duration_seconds=PRE_BLOCK_POPUP_SECONDS,
            )
            return True
        except Exception as exc:
            log_event("PRE_BLOCK_POPUP_FAILED", reason=reason, error=str(exc))
            return False

    def _looks_like_relax_window(process_name: str | None, title: str | None) -> bool:
        process = (process_name or "").strip().lower()
        title_lower = (title or "").strip().lower()
        if process not in relax_browser_processes:
            return False
        return any(keyword in title_lower for keyword in relax_title_keywords)

    def _is_reusable_browser_window(
        process_name: str | None,
        title: str | None,
        *,
        require_relax_keyword: bool,
    ) -> bool:
        process = (process_name or "").strip().lower()
        if process not in relax_browser_processes:
            return False
        title_clean = (title or "").strip()
        if not title_clean:
            return False
        title_lower = title_clean.lower()
        if title_lower in ignored_browser_titles:
            return False
        if require_relax_keyword and not _looks_like_relax_window(process_name, title):
            return False
        return True

    def _is_tracked_relax_window(pid: int, hwnd: int, process_name: str | None, title: str | None) -> bool:
        if relax_primary_hwnd and hwnd == relax_primary_hwnd:
            return True
        if hwnd in relax_window_hwnds:
            return True
        # Fallback only before we have a concrete hwnd tracked.
        if not relax_primary_hwnd and not relax_window_hwnds and pid in relax_window_pids and _looks_like_relax_window(process_name, title):
            return True
        return False

    def _register_relax_launches(launches) -> None:
        nonlocal relax_primary_hwnd
        if not launches:
            return

        for launch in launches:
            if launch.pid:
                relax_window_pids.add(launch.pid)
                matched_launch_window = False
                for win in find_windows_by_pid(launch.pid):
                    if _is_reusable_browser_window(
                        win.process_name,
                        win.title,
                        require_relax_keyword=False,
                    ):
                        relax_window_hwnds.clear()
                        relax_window_hwnds.add(win.hwnd)
                        relax_primary_hwnd = win.hwnd
                        matched_launch_window = True
                        break

                if not matched_launch_window:
                    active = get_active_window_info()
                    if active and _is_reusable_browser_window(
                        active.process_name,
                        active.title,
                        require_relax_keyword=False,
                    ):
                        relax_window_hwnds.clear()
                        relax_window_hwnds.add(active.hwnd)
                        relax_window_pids.add(active.pid)
                        relax_primary_hwnd = active.hwnd

        # Browser windows may appear slightly after process start.
        time.sleep(0.18)
        for launch in launches:
            if launch.pid:
                matched_launch_window = False
                for win in find_windows_by_pid(launch.pid):
                    if _is_reusable_browser_window(
                        win.process_name,
                        win.title,
                        require_relax_keyword=False,
                    ):
                        relax_window_hwnds.clear()
                        relax_window_hwnds.add(win.hwnd)
                        relax_primary_hwnd = win.hwnd
                        matched_launch_window = True
                        break

                if not matched_launch_window:
                    active = get_active_window_info()
                    if active and _is_reusable_browser_window(
                        active.process_name,
                        active.title,
                        require_relax_keyword=False,
                    ):
                        relax_window_hwnds.clear()
                        relax_window_hwnds.add(active.hwnd)
                        relax_window_pids.add(active.pid)
                        relax_primary_hwnd = active.hwnd

        active = get_active_window_info()
        if active and _is_reusable_browser_window(
            active.process_name,
            active.title,
            require_relax_keyword=False,
        ):
            relax_window_pids.add(active.pid)
            relax_window_hwnds.clear()
            relax_window_hwnds.add(active.hwnd)
            relax_primary_hwnd = active.hwnd

    def _get_existing_relax_windows():
        nonlocal relax_primary_hwnd
        candidates = []
        invalid_hwnds: list[int] = []

        for hwnd in relax_window_hwnds:
            info = get_window_info(hwnd)
            if not info:
                invalid_hwnds.append(hwnd)
                continue
            if not _is_reusable_browser_window(
                info.process_name,
                info.title,
                require_relax_keyword=False,
            ):
                invalid_hwnds.append(hwnd)
                continue
            candidates.append(info)

        for hwnd in invalid_hwnds:
            relax_window_hwnds.discard(hwnd)
            if relax_primary_hwnd == hwnd:
                relax_primary_hwnd = None

        # Keep PIDs in sync with currently valid tracked windows.
        if candidates:
            relax_window_pids.clear()
            for win in candidates:
                relax_window_pids.add(win.pid)
            if not relax_primary_hwnd:
                relax_primary_hwnd = candidates[-1].hwnd

        if candidates:
            return candidates

        # Fallback: if only PID survived, rescan windows from PID.
        for pid in list(relax_window_pids):
            wins = find_windows_by_pid(pid)
            if not wins:
                relax_window_pids.discard(pid)
                continue
            for win in wins:
                if _is_reusable_browser_window(
                    win.process_name,
                    win.title,
                    require_relax_keyword=False,
                ):
                    relax_window_hwnds.clear()
                    relax_window_hwnds.add(win.hwnd)
                    candidates.append(win)
                    relax_primary_hwnd = win.hwnd
                    break

        if candidates:
            return candidates

        return candidates

    def _focus_existing_relax_window() -> bool:
        nonlocal relax_primary_hwnd
        candidates = _get_existing_relax_windows()
        if not candidates:
            return False

        # Always prefer the primary tracked relax window.
        win = None
        if relax_primary_hwnd:
            for candidate in candidates:
                if candidate.hwnd == relax_primary_hwnd:
                    win = candidate
                    break
        if win is None:
            win = candidates[-1]
            relax_primary_hwnd = win.hwnd
        ok = focus_relax_window(win.hwnd, maximize=True)
        if ok:
            log_event(
                "RELAX_MEDIA_FOCUSED",
                pid=win.pid,
                hwnd=win.hwnd,
                process=win.process_name,
                title=win.title,
            )
        return ok

    def _run_relax_alert(
        reason: str,
        media_level: int,
        *,
        message: str | None = None,
        respect_cooldown: bool = False,
        reuse_existing_window: bool = False,
    ) -> bool:
        nonlocal relax_session_active
        current = state.snapshot()
        if not current["enabled"]:
            return False

        if reuse_existing_window and _focus_existing_relax_window():
            relax_session_active = True
            if message:
                _show_agent_message(reason, message)
            return True

        # Hard anti-storm guard: if we are re-intervening and couldn't focus an existing
        # relax window, never create new windows too fast.
        if reason in {"BLOCK", "RELAX_ESCAPE"} and not state.media_cooldown_ok(MEDIA_COOLDOWN_SECONDS):
            if not (relax_window_hwnds or relax_window_pids):
                # If there is no known relax window, allow a fresh open attempt.
                pass
            else:
                if message:
                    _show_agent_message(reason, message)
                log_event(
                    "RELAX_MEDIA_SKIPPED",
                    level=media_level,
                    reason=reason,
                    cooldown_seconds=MEDIA_COOLDOWN_SECONDS,
                    guard="anti_storm",
                )
                return False

        if respect_cooldown and not state.media_cooldown_ok(MEDIA_COOLDOWN_SECONDS):
            if message:
                _show_agent_message(reason, message)
            log_event(
                "RELAX_MEDIA_SKIPPED",
                level=media_level,
                reason=reason,
                cooldown_seconds=MEDIA_COOLDOWN_SECONDS,
            )
            return False

        if message:
            _show_agent_message(reason, message)

        requested_urls = resolver.resolve_for_level(media_level)
        launch_urls = requested_urls[: max(1, RELAX_MAX_SIMULTANEOUS_VIDEOS)]

        launches = open_relax_urls(launch_urls)
        _register_relax_launches(launches)
        focused = _focus_existing_relax_window()
        relax_session_active = bool(launches) or focused
        if relax_session_active:
            state.mark_media()
        log_event(
            "RELAX_MEDIA_OPENED",
            level=media_level,
            reason=reason,
            launch_count=len(launches),
            requested_count=len(requested_urls),
            launch_pids=[launch.pid for launch in launches if launch.pid],
        )
        return True

    # Prime runtime values immediately so tray text starts correct.
    state.update_runtime(
        phase=cycle.phase,
        cycle_index=cycle.cycle_index,
        phase_remaining=cycle.phase_remaining(),
        phase_total=cycle.phase_total(),
        rest_seconds_current=cycle.current_rest_seconds(),
        work_seconds_current=cycle.current_work_seconds(),
    )
    log_event("APP_STARTED", dev_mode=state.dev_mode, panic_mode=state.panic_mode)
    time.sleep(1.0)
    _show_agent_message("START", _alert_message("START", cycle.cycle_index))

    last_menu_refresh = 0.0

    while state.snapshot()["running"]:
        transition = cycle.update()
        state.update_runtime(
            phase=cycle.phase,
            cycle_index=cycle.cycle_index,
            phase_remaining=cycle.phase_remaining(),
            phase_total=cycle.phase_total(),
            rest_seconds_current=cycle.current_rest_seconds(),
            work_seconds_current=cycle.current_work_seconds(),
        )

        if transition == "ENTER_WORK":
            state.reset_rest_violations()
            relax_window_hwnds.clear()
            relax_window_pids.clear()
            relax_primary_hwnd = None
            relax_session_active = False
            log_event("ENTER_WORK", cycle=cycle.cycle_index, work_seconds=cycle.current_work_seconds())
            _show_agent_message("ENTER_WORK", _alert_message("ENTER_WORK", cycle.cycle_index))
        elif transition == "ENTER_REST":
            state.reset_rest_violations()
            relax_window_hwnds.clear()
            relax_window_pids.clear()
            relax_primary_hwnd = None
            relax_session_active = False
            log_event("ENTER_REST", cycle=cycle.cycle_index, rest_seconds=cycle.current_rest_seconds())
            _run_relax_alert(
                "ENTER_REST",
                cycle.cycle_index,
                message=_alert_message("ENTER_REST", cycle.cycle_index),
            )

        def _trigger_intervention(
            reason: str,
            media_level: int,
            *,
            attempt_count: int = 0,
            force_media_open: bool = False,
            reuse_existing_window: bool = False,
        ) -> None:
            if not state.snapshot()["enabled"]:
                return

            alert_text = _alert_message(
                reason,
                media_level,
                process_name=info.process_name,
                attempt_count=attempt_count,
            )

            _show_pre_block_popup(reason, alert_text)

            block_productive_window(info.hwnd, info.pid)
            state.mark_block()
            log_event(
                "BLOCKED",
                reason=reason,
                process=info.process_name,
                title=info.title,
                pid=info.pid,
                cycle=cycle.cycle_index,
                phase=cycle.phase,
                attempt_count=attempt_count,
                autocratic=attempt_count >= 2,
            )

            current = state.snapshot()
            if not current["enabled"]:
                return

            _run_relax_alert(
                reason,
                media_level,
                message=alert_text,
                respect_cooldown=not force_media_open,
                reuse_existing_window=reuse_existing_window,
            )

        snap = state.snapshot()
        if snap["enabled"]:
            info = get_active_window_info()
            if info and snap["panic_mode"] and is_panic_target(info.process_name):
                if state.cooldown_ok(PANIC_COOLDOWN_SECONDS):
                    _trigger_intervention(
                        reason="PANIC",
                        media_level=max(cycle.cycle_index, 5),
                    )
            elif info and cycle.phase == REST_FORCED and should_block(info.process_name, snap["dev_mode"]):
                if state.cooldown_ok(BLOCK_COOLDOWN_SECONDS):
                    attempt_count = state.mark_rest_violation()
                    _trigger_intervention(
                        reason="BLOCK",
                        media_level=cycle.cycle_index + max(0, attempt_count - 1),
                        attempt_count=attempt_count,
                        force_media_open=True,
                        reuse_existing_window=True,
                    )
            elif info and cycle.phase == REST_FORCED:
                process_lower = (info.process_name or "").strip().lower()
                escaped_relax_window = (
                    relax_session_active
                    and (len(relax_window_hwnds) > 0 or len(relax_window_pids) > 0)
                    and process_lower in relax_browser_processes
                    and not _is_tracked_relax_window(info.pid, info.hwnd, info.process_name, info.title)
                )
                if escaped_relax_window and state.cooldown_ok(RELAX_ESCAPE_COOLDOWN_SECONDS):
                    attempt_count = state.mark_rest_violation()
                    _trigger_intervention(
                        reason="RELAX_ESCAPE",
                        media_level=cycle.cycle_index + attempt_count,
                        attempt_count=attempt_count,
                        force_media_open=True,
                        reuse_existing_window=True,
                    )

        # Keep dynamic menu text (timers/status) in sync.
        now = time.time()
        if now - last_menu_refresh >= 1.0:
            try:
                request_menu_refresh()
            except Exception:
                pass
            last_menu_refresh = now

        time.sleep(POLL_INTERVAL_SECONDS)

    log_event("APP_STOPPED")


def main() -> None:
    args = parse_args()
    state = resolve_startup_state(args)
    if state is None:
        return

    def on_toggle() -> None:
        enabled = state.toggle_enabled()
        log_event("TOGGLE_ENABLED", enabled=enabled)

    def on_toggle_dev_mode() -> None:
        dev_mode_now = state.toggle_dev_mode()
        log_event("TOGGLE_DEV_MODE", dev_mode=dev_mode_now)

    def on_toggle_panic_mode() -> None:
        panic_mode_now = state.toggle_panic_mode()
        log_event("TOGGLE_PANIC_MODE", panic_mode=panic_mode_now)

    def on_toggle_overlay_mode() -> None:
        overlay_mode_now = state.toggle_overlay_enabled()
        log_event("TOGGLE_NOTIFICATIONS", notifications_enabled=overlay_mode_now)

    def on_quit() -> None:
        state.stop()
        log_event("QUIT_CLICKED")

    tray = build_tray(
        state,
        on_toggle=on_toggle,
        on_toggle_dev_mode=on_toggle_dev_mode,
        on_toggle_panic_mode=on_toggle_panic_mode,
        on_toggle_overlay_mode=on_toggle_overlay_mode,
        on_quit=on_quit,
    )

    def send_notification(title: str, message: str) -> None:
        try:
            tray.notify(message, title=title)
            log_event("NOTIFICATION_SENT", title=title, message=message)
        except Exception as exc:
            log_event("NOTIFICATION_FAILED", error=str(exc), title=title, message=message)

    worker = threading.Thread(
        target=monitor_loop,
        args=(state, tray.update_menu, send_notification),
        daemon=True,
    )
    worker.start()

    tray.run()


if __name__ == "__main__":
    main()
