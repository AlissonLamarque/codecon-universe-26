from __future__ import annotations

import json
import os
import time
from typing import Any

from config import LOG_PATH


def log_event(event: str, **payload: Any) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": event,
        **payload,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")

