from __future__ import annotations

import argparse
import os
import re
import threading
import time
from typing import Callable

from alert_agent import AlertContext, build_alert_message, get_last_alert_backend
from app_state import AppState
from config import (
    BLOCK_COOLDOWN_SECONDS,
    DEV_MODE,
    ENABLE_OVERLAY,
    MEDIA_COOLDOWN_SECONDS,
    PANIC_COOLDOWN_SECONDS,
    POLL_INTERVAL_SECONDS,
    PRE_BLOCK_POPUP_SECONDS,
    PRE_BLOCK_POPUP_MAX_SECONDS,
    PRE_BLOCK_POPUP_STORM_FROM_STAGE,
    PRE_BLOCK_POPUP_STORM_MAX_COPIES,
    PRE_BLOCK_POPUP_STORM_STAGGER_SECONDS,
    PRE_BLOCK_POPUP_STORM_STEP_STAGE,
    PRE_BLOCK_POPUP_STEP_EVERY_ATTEMPTS,
    PRE_BLOCK_POPUP_STEP_SECONDS,
    SIDE_ALERT_BASE_SECONDS,
    SIDE_ALERT_ENABLED,
    SIDE_ALERT_MAX_SECONDS,
    SIDE_ALERT_RIGHT_MARGIN,
    SIDE_ALERT_STAGE_STEP_SECONDS,
    SIDE_ALERT_SUBTITLE,
    SIDE_ALERT_TITLE,
    SIDE_ALERT_TOP_RATIO,
    NOTIFICATION_MODE,
    IMPORTANT_NOTIFICATION_EVERY_ATTEMPTS,
    STATUS_NOTIFICATION_MIN_SECONDS,
    RELAX_BROWSER_PROCESSES,
    RELAX_ESCAPE_COOLDOWN_SECONDS,
    RELAX_MAX_SIMULTANEOUS_VIDEOS,
    RELAX_MULTI_VIDEO_FROM_STAGE_2,
    RELAX_MULTI_VIDEO_FROM_STAGE_3,
    RELAX_TITLE_KEYWORDS,
    REST_EXTENSION_BASE_SECONDS,
    REST_EXTENSION_ENABLED,
    REST_EXTENSION_MAX_PER_EVENT_SECONDS,
    REST_EXTENSION_PER_ATTEMPT_SECONDS,
    REST_EXTENSION_RAGE_BONUS_SECONDS,
    REST_EXTENSION_RAGE_EVERY,
    REST_EXTENSION_START_AFTER_ATTEMPTS,
)
from enforcer import block_productive_window, close_window, focus_relax_window, open_relax_urls
from launcher import show_launcher
from logger_utils import log_event
from monitor import find_windows_by_pid, get_active_window_info, get_window_info
from overlay import dismiss_side_alert_note, show_intervention_popup, show_intervention_popup_storm, show_side_alert_note
from policy import is_panic_target, should_block
from state_machine import CycleState, REST_FORCED
from tray_app import build_tray
from youtube_resolver import YouTubeResolver


def _detect_default_alert_backend_from_env() -> str:
    llm_enabled = os.getenv("AB_ENABLE_LLM_ALERTS", "0").strip().lower() not in {"0", "false", "no", "off", ""}
    backend = os.getenv("AB_ALERT_BACKEND", "auto").strip().lower()
    if llm_enabled and backend in {"ollama", "auto"}:
        return "ollama"
    return "local"


def _apply_startup_alert_backend_choice(alert_backend: str) -> None:
    normalized = (alert_backend or "local").strip().lower()
    if normalized == "ollama":
        os.environ["AB_ENABLE_LLM_ALERTS"] = "1"
        os.environ["AB_ALERT_BACKEND"] = "ollama"
        os.environ.setdefault("AB_ENABLE_OLLAMA_ALERTS", "1")
        return

    os.environ["AB_ENABLE_LLM_ALERTS"] = "0"
    os.environ["AB_ALERT_BACKEND"] = "local"


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
        default_alert_backend = _detect_default_alert_backend_from_env()
        launch = show_launcher(
            default_dev_mode=DEV_MODE,
            default_panic_mode=False,
            default_overlay_enabled=ENABLE_OVERLAY,
            default_enabled=True,
            default_alert_backend=default_alert_backend,
        )
        if launch is None:
            return None
        _apply_startup_alert_backend_choice(launch.alert_backend)
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
    relax_media_stage_opened = -1
    relax_browser_processes = {name.lower() for name in RELAX_BROWSER_PROCESSES}
    relax_title_keywords = tuple(keyword.lower() for keyword in RELAX_TITLE_KEYWORDS)
    ignored_browser_titles = {"default ime", "msctfime ui"}
    last_windows_toast_at = 0.0

    def _refresh_runtime_state() -> None:
        state.update_runtime(
            phase=cycle.phase,
            cycle_index=cycle.cycle_index,
            phase_remaining=cycle.phase_remaining(),
            phase_total=cycle.phase_total(),
            rest_seconds_current=cycle.current_rest_seconds(),
            rest_extension_seconds=cycle.rest_extension_seconds,
            work_seconds_current=cycle.current_work_seconds(),
        )

    def _madness_stage(reason: str, media_level: int, attempt_count: int) -> int:
        score = max(0, int(attempt_count) - 1)
        if reason == "RELAX_ESCAPE":
            score += 1
        elif reason == "PANIC":
            score += 3

        # Later cycles also start slightly more chaotic.
        score += max(0, media_level // 3)

        # Start slower, then accelerate stage growth so media rotation
        # becomes more frequent after user keeps insisting.
        if score < 3:
            return 0
        if score < 5:
            return 1
        if score < 7:
            return 2
        if score < 9:
            return 3
        if score < 12:
            return 4

        # Infinite escalation: once absurd tier is reached, grow faster
        # (new stage each +2 score) to rotate videos more aggressively.
        return 5 + ((score - 12) // 2)

    def _media_hint(media_level: int, reason: str, attempt_count: int) -> str:
        stage = _madness_stage(reason, media_level, attempt_count)
        return resolver.hint_for_stage(stage)

    def _alert_message(
        event: str,
        media_level: int,
        *,
        process_name: str | None = None,
        attempt_count: int = 0,
        media_hint_override: str | None = None,
    ) -> str:
        snap = state.snapshot()
        effective_media_hint = media_hint_override or _media_hint(media_level, event, attempt_count)
        message = build_alert_message(
            AlertContext(
                event=event,
                phase=cycle.phase,
                cycle_index=cycle.cycle_index,
                process_name=process_name,
                media_hint=effective_media_hint,
                panic_mode=snap["panic_mode"],
                work_seconds=cycle.current_work_seconds(),
                rest_seconds=cycle.current_rest_seconds(),
                attempt_count=attempt_count,
                autocratic=attempt_count >= 2,
            )
        )
        state.set_last_alert_backend(get_last_alert_backend())
        return message

    def _rest_penalty_seconds(reason: str, attempt_count: int) -> int:
        attempt = max(1, int(attempt_count))
        rage_every = max(1, int(REST_EXTENSION_RAGE_EVERY))
        base = max(0, int(REST_EXTENSION_BASE_SECONDS))
        per_attempt = max(0, int(REST_EXTENSION_PER_ATTEMPT_SECONDS))
        rage_bonus = max(0, int(REST_EXTENSION_RAGE_BONUS_SECONDS))
        max_per_event = max(0, int(REST_EXTENSION_MAX_PER_EVENT_SECONDS))

        # Smoother growth: linear + periodic rage bumps.
        penalty = base + (attempt - 1) * per_attempt
        penalty += ((attempt - 1) // rage_every) * rage_bonus
        if reason == "RELAX_ESCAPE":
            penalty += max(1, per_attempt)
        if max_per_event > 0:
            penalty = min(penalty, max_per_event)
        return max(1, penalty)

    def _extend_rest_if_needed(reason: str, attempt_count: int) -> int:
        if not REST_EXTENSION_ENABLED:
            return 0
        if cycle.phase != REST_FORCED:
            return 0
        if reason not in {"BLOCK", "RELAX_ESCAPE"}:
            return 0
        start_after = max(0, int(REST_EXTENSION_START_AFTER_ATTEMPTS))
        if attempt_count <= start_after:
            return 0

        effective_attempt = max(1, attempt_count - start_after)
        requested = _rest_penalty_seconds(reason, effective_attempt)
        added = cycle.extend_current_rest(requested)
        if added > 0:
            _refresh_runtime_state()
            log_event(
                "REST_EXTENDED",
                reason=reason,
                attempt_count=attempt_count,
                effective_attempt=effective_attempt,
                start_after_attempts=start_after,
                requested_seconds=requested,
                added_seconds=added,
                rest_extension_seconds=cycle.rest_extension_seconds,
                rest_total_seconds=cycle.current_rest_seconds(),
                rest_remaining_seconds=cycle.phase_remaining(),
            )
        return added

    def _fmt_mmss(seconds: int) -> str:
        m, s = divmod(max(0, int(seconds)), 60)
        return f"{m:02d}:{s:02d}"

    def _phase_label() -> str:
        return "DESCANSO" if cycle.phase == REST_FORCED else "PRODUTIVIDADE"

    def _status_toast_payload(
        reason: str,
        message: str,
        *,
        attempt_count: int = 0,
        added_rest: int = 0,
    ) -> tuple[str, str] | None:
        remaining = _fmt_mmss(cycle.phase_remaining())
        rest_total = _fmt_mmss(cycle.current_rest_seconds())
        work_total = _fmt_mmss(cycle.current_work_seconds())
        phase = _phase_label()

        mode = NOTIFICATION_MODE if NOTIFICATION_MODE in {"status", "all"} else "status"
        if mode == "all":
            return ("Anti-Burnout", message)

        if reason == "START":
            return ("Anti-Burnout", f"Iniciado | Estado: {phase} | Faltam {remaining}")
        if reason == "ENTER_REST":
            return (
                "Anti-Burnout",
                f"Estado: DESCANSO | Faltam {remaining} | Descanso total {rest_total}",
            )
        if reason == "ENTER_WORK":
            return (
                "Anti-Burnout",
                f"Estado: PRODUTIVIDADE | Faltam {remaining} | Trabalho total {work_total}",
            )

        # Status mode: interventions only occasionally and only when relevant.
        important_every = max(2, int(IMPORTANT_NOTIFICATION_EVERY_ATTEMPTS))
        important = (
            reason == "PANIC"
            or (attempt_count > 0 and attempt_count % important_every == 0)
            or added_rest >= 12
        )
        if not important:
            return None

        if reason == "PANIC":
            return (
                "Anti-Burnout",
                f"Alerta PANICO | Estado: {phase} | Faltam {remaining}",
            )

        if added_rest > 0:
            return (
                "Anti-Burnout",
                f"Intervencao forte | Tentativa {attempt_count} | +{added_rest}s de descanso | Faltam {remaining}",
            )

        return (
            "Anti-Burnout",
            f"Intervencao anti-burnout | Tentativa {attempt_count} | Estado: {phase} | Faltam {remaining}",
        )

    def _show_agent_message(
        reason: str,
        message: str,
        *,
        attempt_count: int = 0,
        added_rest: int = 0,
        force_toast: bool = False,
    ) -> bool:
        nonlocal last_windows_toast_at
        current = state.snapshot()
        if not current["enabled"] or not current["overlay_enabled"]:
            return False

        toast_payload = _status_toast_payload(
            reason,
            message,
            attempt_count=attempt_count,
            added_rest=added_rest,
        )
        if force_toast and toast_payload is None:
            toast_payload = ("Anti-Burnout", message)

        if toast_payload is not None:
            now = time.time()
            min_gap = max(0.0, float(STATUS_NOTIFICATION_MIN_SECONDS))
            if force_toast or now - last_windows_toast_at >= min_gap:
                title, body = toast_payload
                send_notification(title, body)
                last_windows_toast_at = now
            else:
                log_event(
                    "NOTIFICATION_SKIPPED",
                    reason=reason,
                    throttle_seconds=min_gap,
                )

        log_event("ALERT_SHOWN", reason=reason, message=message)
        return True

    def _popup_duration_seconds(reason: str, attempt_count: int, added_rest: int) -> float:
        base = max(1.0, float(PRE_BLOCK_POPUP_SECONDS))
        max_seconds = max(base, float(PRE_BLOCK_POPUP_MAX_SECONDS))
        step_every = max(1, int(PRE_BLOCK_POPUP_STEP_EVERY_ATTEMPTS))
        step_seconds = max(0.0, float(PRE_BLOCK_POPUP_STEP_SECONDS))

        if reason not in {"BLOCK", "RELAX_ESCAPE", "PANIC"}:
            return base

        steps = max(0, int(attempt_count) - 1) // step_every
        extra = steps * step_seconds
        if reason == "PANIC":
            extra += step_seconds
        if added_rest >= 20:
            extra += step_seconds

        return min(max_seconds, base + extra)

    def _popup_storm_copies(madness_stage: int, attempt_count: int) -> int:
        max_copies = max(1, int(PRE_BLOCK_POPUP_STORM_MAX_COPIES))
        start_stage = max(1, int(PRE_BLOCK_POPUP_STORM_FROM_STAGE))
        step_stage = max(1, int(PRE_BLOCK_POPUP_STORM_STEP_STAGE))

        if madness_stage < start_stage:
            return 1

        stage_steps = 1 + ((madness_stage - start_stage) // step_stage)
        attempt_boost = max(0, int(attempt_count) - 7) // 6
        copies = 1 + stage_steps + attempt_boost
        return min(max_copies, max(1, copies))

    def _parallel_relax_windows_for_stage(madness_stage: int) -> int:
        cap = max(1, int(RELAX_MAX_SIMULTANEOUS_VIDEOS))
        stage_for_three = max(0, int(RELAX_MULTI_VIDEO_FROM_STAGE_3))
        stage_for_two = max(0, int(RELAX_MULTI_VIDEO_FROM_STAGE_2))

        if madness_stage >= stage_for_three:
            return min(cap, 3)
        if madness_stage >= stage_for_two:
            return min(cap, 2)
        return 1

    def _side_alert_duration_seconds(madness_stage: int, attempt_count: int, added_rest: int) -> float:
        base = max(4.0, float(SIDE_ALERT_BASE_SECONDS))
        max_seconds = max(base, float(SIDE_ALERT_MAX_SECONDS))
        stage_step = max(0.0, float(SIDE_ALERT_STAGE_STEP_SECONDS))

        extra = max(0, madness_stage) * stage_step
        extra += max(0, int(attempt_count) - 4) * 0.55
        if added_rest > 0:
            extra += min(8.0, float(added_rest) / 5.0)
        return min(max_seconds, base + extra)

    def _fallback_side_alert_text(reason: str, *, added_rest: int = 0) -> str:
        remaining = _fmt_mmss(cycle.phase_remaining())
        if reason == "ENTER_REST":
            return f"Descanso ON. Faltam {remaining}. Fica no video relax e respira um pouco."
        if reason == "PANIC":
            return f"Modo panico anti-burnout ligado. Faltam {remaining}. Sem produtividade agora."

        base = f"Te bloqueei no descanso. Faltam {remaining}."
        if added_rest > 0:
            base += f" Tu insistiu e ganhou +{added_rest}s."
        return base + " Volta pro video relax."

    def _normalize_side_alert_text(reason: str, message: str | None, *, added_rest: int = 0) -> str:
        raw = (message or "").replace("\r", " ").replace("\n", " ")
        text = " ".join(raw.split()).strip()
        if not text:
            return _fallback_side_alert_text(reason, added_rest=added_rest)

        # Remove technical artifacts and partial tokens from buggy model output.
        text = re.sub(r"(?i)\brest\s*forc(?:ed)?\.?\b", "", text)
        text = re.sub(r"(?i)\b(block|relax_escape|rest_forced|enter_rest|enter_work|productive_window)\b", "", text)
        text = re.sub(r"(?i)\bvsc\s*code\b", "VS Code", text)
        text = text.replace("_", " ")
        text = re.sub(r"(?i)por\s+que\?\s+porque", "Porque", text)
        text = text.replace("\" - ", " ")
        text = text.replace("' - ", " ")
        text = re.sub(r"\s{2,}", " ", text).strip(" .:-")

        if not text:
            return _fallback_side_alert_text(reason, added_rest=added_rest)

        # Keep only complete sentences where possible.
        parts = re.findall(r"[^.!?]+[.!?]", text)
        if parts:
            candidate = " ".join(" ".join(p.split()).strip() for p in parts[:2]).strip()
            if candidate:
                text = candidate

        text = text.strip().strip("\"'`- ").strip()
        if not text:
            return _fallback_side_alert_text(reason, added_rest=added_rest)

        suspicious = (
            bool(re.search(r"(?i)\brest\s*forc", text))
            or bool(re.search(r"(?i)\bporque\s+precisamos\s+de\s*$", text))
            or text.endswith(":")
            or text.endswith("...")
            or len([c for c in text if c.isalpha()]) < 18
        )
        if suspicious:
            return _fallback_side_alert_text(reason, added_rest=added_rest)

        max_len = 240
        if len(text) > max_len:
            clipped = text[:max_len].rstrip()
            if " " in clipped:
                clipped = clipped.rsplit(" ", 1)[0].rstrip()
            text = clipped.strip()
            if not text:
                return _fallback_side_alert_text(reason, added_rest=added_rest)

        if text[-1] not in ".!?":
            text += "."
        return text

    def _maybe_show_side_alert(
        reason: str,
        message: str | None,
        *,
        madness_stage: int,
        attempt_count: int = 0,
        added_rest: int = 0,
    ) -> None:
        if not SIDE_ALERT_ENABLED:
            return
        if reason not in {"ENTER_REST", "BLOCK", "RELAX_ESCAPE", "PANIC"}:
            return
        text = _normalize_side_alert_text(reason, message, added_rest=added_rest)
        if not text:
            return

        duration = _side_alert_duration_seconds(madness_stage, attempt_count, added_rest)
        show_side_alert_note(
            text,
            duration_seconds=duration,
            right_margin=max(8, int(SIDE_ALERT_RIGHT_MARGIN)),
            top_ratio=max(0.05, min(0.8, float(SIDE_ALERT_TOP_RATIO))),
            title=(SIDE_ALERT_TITLE or "Espirito de Epicuro"),
            subtitle=(SIDE_ALERT_SUBTITLE or "Ataraxia assistida"),
        )
        log_event(
            "SIDE_ALERT_SHOWN",
            reason=reason,
            madness_stage=madness_stage,
            duration_seconds=duration,
            attempt_count=attempt_count,
            added_rest=added_rest,
        )

    def _show_pre_block_popup(
        reason: str,
        message: str,
        *,
        madness_stage: int = 0,
        attempt_count: int = 0,
        added_rest: int = 0,
    ) -> bool:
        current = state.snapshot()
        if not current["enabled"] or not current["overlay_enabled"]:
            return False

        # Hide persistent side note while the centered intervention popup is visible.
        dismiss_side_alert_note()

        duration = _popup_duration_seconds(reason, attempt_count, added_rest)
        copies = _popup_storm_copies(madness_stage, attempt_count)
        try:
            if copies <= 1:
                show_intervention_popup(message, duration_seconds=duration)
            else:
                show_intervention_popup_storm(
                    message,
                    copies=copies,
                    duration_seconds=duration,
                    stagger_seconds=max(0.0, float(PRE_BLOCK_POPUP_STORM_STAGGER_SECONDS)),
                    flash=True,
                    wait_first=True,
                )
            log_event(
                "PRE_BLOCK_POPUP_SHOWN",
                reason=reason,
                duration_seconds=duration,
                copies=copies,
                madness_stage=madness_stage,
                attempt_count=attempt_count,
                added_rest=added_rest,
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

    def _clear_relax_tracking() -> None:
        nonlocal relax_primary_hwnd, relax_media_stage_opened, relax_session_active
        relax_window_hwnds.clear()
        relax_window_pids.clear()
        relax_primary_hwnd = None
        relax_session_active = False
        relax_media_stage_opened = -1

    def _close_existing_relax_windows(*, reason: str, target_stage: int) -> int:
        windows = _get_existing_relax_windows()
        if not windows:
            _clear_relax_tracking()
            return 0

        closed = 0
        seen_hwnds: set[int] = set()
        for win in windows:
            if win.hwnd in seen_hwnds:
                continue
            seen_hwnds.add(win.hwnd)
            if close_window(win.hwnd):
                closed += 1

        # Give browser a short moment to process WM_CLOSE.
        if closed > 0:
            time.sleep(0.14)

        log_event(
            "RELAX_MEDIA_ROTATED",
            reason=reason,
            target_stage=target_stage,
            closed_windows=closed,
        )
        _clear_relax_tracking()
        return closed

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
        attempt_count: int = 0,
        added_rest: int = 0,
        message: str | None = None,
        respect_cooldown: bool = False,
        reuse_existing_window: bool = False,
        force_replace_existing: bool = False,
    ) -> bool:
        nonlocal relax_session_active, relax_media_stage_opened
        current = state.snapshot()
        if not current["enabled"]:
            return False

        madness_stage = _madness_stage(reason, media_level, attempt_count)
        stage_escalated = madness_stage > relax_media_stage_opened
        should_rotate_media = (
            force_replace_existing
            or (
                reuse_existing_window
                and relax_session_active
                and stage_escalated
                and len(_get_existing_relax_windows()) > 0
            )
        )

        if should_rotate_media:
            _close_existing_relax_windows(reason=reason, target_stage=madness_stage)

        if reuse_existing_window and not should_rotate_media and _focus_existing_relax_window():
            relax_session_active = True
            if message:
                _show_agent_message(reason, message, attempt_count=attempt_count, added_rest=added_rest)
                _maybe_show_side_alert(
                    reason,
                    message,
                    madness_stage=madness_stage,
                    attempt_count=attempt_count,
                    added_rest=added_rest,
                )
            return True

        # Hard anti-storm guard: if we are re-intervening and couldn't focus an existing
        # relax window, never create new windows too fast.
        if reason in {"BLOCK", "RELAX_ESCAPE"} and not state.media_cooldown_ok(MEDIA_COOLDOWN_SECONDS):
            if not (relax_window_hwnds or relax_window_pids):
                # If there is no known relax window, allow a fresh open attempt.
                pass
            else:
                if message:
                    _show_agent_message(reason, message, attempt_count=attempt_count, added_rest=added_rest)
                    _maybe_show_side_alert(
                        reason,
                        message,
                        madness_stage=madness_stage,
                        attempt_count=attempt_count,
                        added_rest=added_rest,
                    )
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
                _show_agent_message(reason, message, attempt_count=attempt_count, added_rest=added_rest)
                _maybe_show_side_alert(
                    reason,
                    message,
                    madness_stage=madness_stage,
                    attempt_count=attempt_count,
                    added_rest=added_rest,
                )
            log_event(
                "RELAX_MEDIA_SKIPPED",
                level=media_level,
                reason=reason,
                cooldown_seconds=MEDIA_COOLDOWN_SECONDS,
            )
            return False

        if message:
            _show_agent_message(reason, message, attempt_count=attempt_count, added_rest=added_rest)

        parallel_target = _parallel_relax_windows_for_stage(madness_stage)
        requested_urls, hint = resolver.resolve_for_mode(
            media_level=media_level,
            madness_stage=madness_stage,
            max_urls=parallel_target,
        )
        launch_urls = requested_urls[:parallel_target]

        launches = open_relax_urls(launch_urls)
        _register_relax_launches(launches)
        focused = _focus_existing_relax_window()
        relax_session_active = bool(launches) or focused
        if relax_session_active:
            relax_media_stage_opened = max(relax_media_stage_opened, madness_stage)
            state.mark_media()
            if message:
                _maybe_show_side_alert(
                    reason,
                    message,
                    madness_stage=madness_stage,
                    attempt_count=attempt_count,
                    added_rest=added_rest,
                )
        log_event(
            "RELAX_MEDIA_OPENED",
            level=media_level,
            reason=reason,
            madness_stage=madness_stage,
            stage_escalated=stage_escalated,
            media_hint=hint,
            parallel_target=parallel_target,
            launch_count=len(launches),
            requested_count=len(requested_urls),
            launch_pids=[launch.pid for launch in launches if launch.pid],
        )
        return True

    # Prime runtime values immediately so tray text starts correct.
    _refresh_runtime_state()
    log_event("APP_STARTED", dev_mode=state.dev_mode, panic_mode=state.panic_mode)
    time.sleep(1.0)
    _show_agent_message("START", _alert_message("START", cycle.cycle_index), force_toast=True)

    last_menu_refresh = 0.0

    while state.snapshot()["running"]:
        transition = cycle.update()
        _refresh_runtime_state()

        if transition == "ENTER_WORK":
            state.reset_rest_violations()
            _clear_relax_tracking()
            log_event("ENTER_WORK", cycle=cycle.cycle_index, work_seconds=cycle.current_work_seconds())
            _show_agent_message("ENTER_WORK", _alert_message("ENTER_WORK", cycle.cycle_index), force_toast=True)
        elif transition == "ENTER_REST":
            state.reset_rest_violations()
            _clear_relax_tracking()
            log_event("ENTER_REST", cycle=cycle.cycle_index, rest_seconds=cycle.current_rest_seconds())
            _run_relax_alert(
                "ENTER_REST",
                cycle.cycle_index,
                attempt_count=0,
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

            added_rest = _extend_rest_if_needed(reason, attempt_count)
            tracked_relax_window_exists = relax_session_active and (len(relax_window_hwnds) > 0 or len(relax_window_pids) > 0)
            target_stage = _madness_stage(reason, media_level, attempt_count)
            should_replace_existing = tracked_relax_window_exists and target_stage > relax_media_stage_opened
            media_hint_override = None
            if reuse_existing_window and tracked_relax_window_exists and not should_replace_existing:
                media_hint_override = "video de relax atual"
            elif reason in {"BLOCK", "RELAX_ESCAPE", "PANIC"}:
                media_hint_override = resolver.hint_for_stage(target_stage)
            alert_text = _alert_message(
                reason,
                media_level,
                process_name=info.process_name,
                attempt_count=attempt_count,
                media_hint_override=media_hint_override,
            )
            if added_rest > 0:
                penalty_tails = [
                    f"Tu insistiu, entao subi teu descanso em +{added_rest}s.",
                    f"Teimosia cobrou pedagio: +{added_rest}s de pausa.",
                    f"Quis burlar de novo, ganhou +{added_rest}s de descanso.",
                ]
                penalty_tail = penalty_tails[(cycle.cycle_index + max(0, attempt_count)) % len(penalty_tails)]
                alert_text = f"{alert_text} {penalty_tail}"

            _show_pre_block_popup(
                reason,
                alert_text,
                madness_stage=target_stage,
                attempt_count=attempt_count,
                added_rest=added_rest,
            )

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
                attempt_count=attempt_count,
                added_rest=added_rest,
                message=alert_text,
                respect_cooldown=not force_media_open,
                reuse_existing_window=reuse_existing_window,
                force_replace_existing=should_replace_existing,
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
