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
    RELAX_QUERIES,
)
from enforcer import block_productive_window, open_relax_urls
from launcher import show_launcher
from logger_utils import log_event
from monitor import get_active_window_info
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

    def _run_relax_alert(
        reason: str,
        media_level: int,
        *,
        message: str | None = None,
        respect_cooldown: bool = False,
    ) -> bool:
        current = state.snapshot()
        if not current["enabled"]:
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

        state.mark_media()

        if message:
            _show_agent_message(reason, message)

        open_relax_urls(resolver.resolve_for_level(media_level))
        log_event("RELAX_MEDIA_OPENED", level=media_level, reason=reason)
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
            log_event("ENTER_WORK", cycle=cycle.cycle_index, work_seconds=cycle.current_work_seconds())
            _show_agent_message("ENTER_WORK", _alert_message("ENTER_WORK", cycle.cycle_index))
        elif transition == "ENTER_REST":
            state.reset_rest_violations()
            log_event("ENTER_REST", cycle=cycle.cycle_index, rest_seconds=cycle.current_rest_seconds())
            _run_relax_alert(
                "ENTER_REST",
                cycle.cycle_index,
                message=_alert_message("ENTER_REST", cycle.cycle_index),
            )

        def _trigger_intervention(reason: str, media_level: int, *, attempt_count: int = 0) -> None:
            if not state.snapshot()["enabled"]:
                return

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
                message=_alert_message(
                    reason,
                    media_level,
                    process_name=info.process_name,
                    attempt_count=attempt_count,
                ),
                respect_cooldown=True,
            )

        snap = state.snapshot()
        # In REST mode, keep intervention aggressive: every new productive attempt
        # should be minimized and redirected to relax content.
        cooldown = PANIC_COOLDOWN_SECONDS if snap["panic_mode"] else BLOCK_COOLDOWN_SECONDS
        if snap["enabled"] and state.cooldown_ok(cooldown):
            info = get_active_window_info()
            if info and snap["panic_mode"] and is_panic_target(info.process_name):
                _trigger_intervention(
                    reason="PANIC",
                    media_level=max(cycle.cycle_index, 5),
                )
            elif info and cycle.phase == REST_FORCED and should_block(info.process_name, snap["dev_mode"]):
                attempt_count = state.mark_rest_violation()
                _trigger_intervention(
                    reason="BLOCK",
                    media_level=cycle.cycle_index + max(0, attempt_count - 1),
                    attempt_count=attempt_count,
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
