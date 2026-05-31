from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class AppState:
    running: bool = True
    enabled: bool = True
    dev_mode: bool = True
    panic_mode: bool = False
    overlay_enabled: bool = True
    timer_overlay_enabled: bool = True
    phase: str = "REST_FORCED"
    cycle_index: int = 0
    phase_remaining: int = 0
    phase_total: int = 0
    rest_seconds_current: int = 0
    work_seconds_current: int = 0
    last_block_at: float = 0.0
    last_media_at: float = 0.0
    rest_violation_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "enabled": self.enabled,
                "dev_mode": self.dev_mode,
                "panic_mode": self.panic_mode,
                "overlay_enabled": self.overlay_enabled,
                "timer_overlay_enabled": self.timer_overlay_enabled,
                "phase": self.phase,
                "cycle_index": self.cycle_index,
                "phase_remaining": self.phase_remaining,
                "phase_total": self.phase_total,
                "rest_seconds_current": self.rest_seconds_current,
                "work_seconds_current": self.work_seconds_current,
                "last_block_at": self.last_block_at,
                "last_media_at": self.last_media_at,
                "rest_violation_count": self.rest_violation_count,
            }

    def toggle_enabled(self) -> bool:
        with self.lock:
            self.enabled = not self.enabled
            return self.enabled

    def toggle_dev_mode(self) -> bool:
        with self.lock:
            self.dev_mode = not self.dev_mode
            return self.dev_mode

    def toggle_panic_mode(self) -> bool:
        with self.lock:
            self.panic_mode = not self.panic_mode
            return self.panic_mode

    def toggle_overlay_enabled(self) -> bool:
        with self.lock:
            self.overlay_enabled = not self.overlay_enabled
            return self.overlay_enabled

    def toggle_timer_overlay(self) -> bool:
        with self.lock:
            self.timer_overlay_enabled = not self.timer_overlay_enabled
            return self.timer_overlay_enabled

    def stop(self) -> None:
        with self.lock:
            self.running = False

    def mark_block(self) -> None:
        with self.lock:
            self.last_block_at = time.time()

    def mark_media(self) -> None:
        with self.lock:
            self.last_media_at = time.time()

    def mark_rest_violation(self) -> int:
        with self.lock:
            self.rest_violation_count += 1
            return self.rest_violation_count

    def reset_rest_violations(self) -> None:
        with self.lock:
            self.rest_violation_count = 0

    def cooldown_ok(self, seconds: float) -> bool:
        with self.lock:
            return (time.time() - self.last_block_at) >= seconds

    def media_cooldown_ok(self, seconds: float) -> bool:
        with self.lock:
            return (time.time() - self.last_media_at) >= seconds

    def update_runtime(
        self,
        *,
        phase: str,
        cycle_index: int,
        phase_remaining: int,
        phase_total: int,
        rest_seconds_current: int,
        work_seconds_current: int,
    ) -> None:
        with self.lock:
            self.phase = phase
            self.cycle_index = cycle_index
            self.phase_remaining = phase_remaining
            self.phase_total = phase_total
            self.rest_seconds_current = rest_seconds_current
            self.work_seconds_current = work_seconds_current
