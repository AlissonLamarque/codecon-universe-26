from __future__ import annotations

import time
from dataclasses import dataclass, field

from config import REST_EXTENSION_MAX_TOTAL_SECONDS, REST_SCHEDULE, WORK_SCHEDULE

REST_FORCED = "REST_FORCED"
PRODUCTIVE_WINDOW = "PRODUCTIVE_WINDOW"


@dataclass
class CycleState:
    phase: str = REST_FORCED
    cycle_index: int = 0
    rest_extension_seconds: int = 0
    phase_started_at: float = field(default_factory=time.time)

    def current_base_rest_seconds(self) -> int:
        idx = min(self.cycle_index, len(REST_SCHEDULE) - 1)
        return REST_SCHEDULE[idx]

    def current_rest_seconds(self) -> int:
        return self.current_base_rest_seconds() + max(0, self.rest_extension_seconds)

    def current_work_seconds(self) -> int:
        idx = min(self.cycle_index, len(WORK_SCHEDULE) - 1)
        return WORK_SCHEDULE[idx]

    def phase_elapsed(self) -> float:
        return time.time() - self.phase_started_at

    def phase_total(self) -> int:
        if self.phase == REST_FORCED:
            return self.current_rest_seconds()
        return self.current_work_seconds()

    def phase_remaining(self) -> int:
        return max(0, int(self.phase_total() - self.phase_elapsed()))

    def update(self) -> str | None:
        if self.phase == REST_FORCED and self.phase_elapsed() >= self.current_rest_seconds():
            self.phase = PRODUCTIVE_WINDOW
            self.rest_extension_seconds = 0
            self.phase_started_at = time.time()
            return "ENTER_WORK"

        if self.phase == PRODUCTIVE_WINDOW and self.phase_elapsed() >= self.current_work_seconds():
            self.phase = REST_FORCED
            self.rest_extension_seconds = 0
            self.phase_started_at = time.time()
            self.cycle_index += 1
            return "ENTER_REST"

        return None

    def extend_current_rest(self, add_seconds: int) -> int:
        if self.phase != REST_FORCED:
            return 0

        requested = max(0, int(add_seconds))
        if requested <= 0:
            return 0

        current_total = self.current_rest_seconds()
        max_total = int(REST_EXTENSION_MAX_TOTAL_SECONDS)
        if max_total > 0:
            target_total = min(max_total, current_total + requested)
            actual_add = max(0, target_total - current_total)
        else:
            actual_add = requested

        self.rest_extension_seconds += actual_add
        return actual_add

