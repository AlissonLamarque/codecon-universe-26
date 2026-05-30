from __future__ import annotations

import argparse
import threading
import time

from app_state import AppState
from config import (
    BLOCK_COOLDOWN_SECONDS,
    DEV_MODE,
    ENABLE_OVERLAY,
    OVERLAY_SECONDS,
    PANIC_COOLDOWN_SECONDS,
    POLL_INTERVAL_SECONDS,
)
from enforcer import block_productive_window, open_relax_urls
from logger_utils import log_event
from monitor import get_active_window_info
from overlay import show_alert_overlay
from policy import is_panic_target, should_block
from state_machine import CycleState, REST_FORCED
from tray_app import build_tray
from youtube_resolver import YouTubeResolver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Anti-Burnout app")
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
        help="Disable the flashing alert overlay.",
    )
    return parser.parse_args()


def monitor_loop(state: AppState, overlay_enabled: bool, request_menu_refresh) -> None:
    resolver = YouTubeResolver()
    cycle = CycleState()

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
    open_relax_urls(resolver.resolve_for_level(cycle.cycle_index))
    log_event("RELAX_MEDIA_OPENED", level=cycle.cycle_index, reason="START")

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
            log_event("ENTER_WORK", cycle=cycle.cycle_index, work_seconds=cycle.current_work_seconds())
        elif transition == "ENTER_REST":
            log_event("ENTER_REST", cycle=cycle.cycle_index, rest_seconds=cycle.current_rest_seconds())
            open_relax_urls(resolver.resolve_for_level(cycle.cycle_index))
            log_event("RELAX_MEDIA_OPENED", level=cycle.cycle_index, reason="ENTER_REST")

        def _trigger_intervention(reason: str, message: str, media_level: int) -> None:
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
            )

            if overlay_enabled:
                show_alert_overlay(message, duration_seconds=OVERLAY_SECONDS)

            open_relax_urls(resolver.resolve_for_level(media_level))
            log_event("RELAX_MEDIA_OPENED", level=media_level, reason=reason)

        snap = state.snapshot()
        cooldown = PANIC_COOLDOWN_SECONDS if snap["panic_mode"] else BLOCK_COOLDOWN_SECONDS
        if snap["enabled"] and state.cooldown_ok(cooldown):
            info = get_active_window_info()
            if info and snap["panic_mode"] and is_panic_target(info.process_name):
                _trigger_intervention(
                    reason="PANIC",
                    message="MODO PANICO: VS CODE DETECTADO!\nINJETANDO DESCANSO FORCADO.",
                    media_level=max(cycle.cycle_index, 5),
                )
            elif info and cycle.phase == REST_FORCED and should_block(info.process_name, snap["dev_mode"]):
                _trigger_intervention(
                    reason="BLOCK",
                    message="NIVEIS DE DOPAMINA CRITICAMENTE BAIXOS!\nDESCANSO OBRIGATORIO INICIADO.",
                    media_level=cycle.cycle_index,
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

    if args.live:
        dev_mode = False
    elif args.dev:
        dev_mode = True
    else:
        dev_mode = DEV_MODE

    overlay_enabled = ENABLE_OVERLAY and not args.no_overlay

    state = AppState(dev_mode=dev_mode)

    def on_toggle() -> None:
        enabled = state.toggle_enabled()
        log_event("TOGGLE_ENABLED", enabled=enabled)

    def on_toggle_dev_mode() -> None:
        dev_mode_now = state.toggle_dev_mode()
        log_event("TOGGLE_DEV_MODE", dev_mode=dev_mode_now)

    def on_toggle_panic_mode() -> None:
        panic_mode_now = state.toggle_panic_mode()
        log_event("TOGGLE_PANIC_MODE", panic_mode=panic_mode_now)

    def on_quit() -> None:
        state.stop()
        log_event("QUIT_CLICKED")

    tray = build_tray(
        state,
        on_toggle=on_toggle,
        on_toggle_dev_mode=on_toggle_dev_mode,
        on_toggle_panic_mode=on_toggle_panic_mode,
        on_quit=on_quit,
    )

    worker = threading.Thread(
        target=monitor_loop,
        args=(state, overlay_enabled, tray.update_menu),
        daemon=True,
    )
    worker.start()

    tray.run()


if __name__ == "__main__":
    main()
