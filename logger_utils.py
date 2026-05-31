from __future__ import annotations

import json
import os
import time
from collections import deque
from typing import Any, Optional

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

def get_last_log() -> Optional[dict[str, Any]]:
    """
    Lê o arquivo de log e retorna o último evento registrado como um dicionário.
    Retorna None se o arquivo não existir ou estiver vazio.
    """
    if not os.path.exists(LOG_PATH):
        return None

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            # O deque com maxlen=1 vai manter apenas a última linha lida na memória
            last_line = deque(f, maxlen=1)
            
            if last_line and last_line[0].strip():
                return json.loads(last_line[0])
            
            return None
            
    except (json.JSONDecodeError, OSError) as e:
        # Evita que o programa quebre caso o arquivo esteja corrompido ou em uso
        print(f"Erro ao ler o último log: {e}")
        return None