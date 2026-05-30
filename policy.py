from __future__ import annotations

from config import DEV_MODE_ALLOWLIST, PANIC_TARGET_APPS, PRODUCTIVE_APPS, PROTECTED_APPS


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


_PRODUCTIVE = {_norm(p) for p in PRODUCTIVE_APPS}
_PROTECTED = {_norm(p) for p in PROTECTED_APPS}
_DEV_ALLOWLIST = {_norm(p) for p in DEV_MODE_ALLOWLIST}
_PANIC_TARGETS = {_norm(p) for p in PANIC_TARGET_APPS}


def is_productive(process_name: str | None) -> bool:
    return _norm(process_name) in _PRODUCTIVE


def is_protected(process_name: str | None) -> bool:
    return _norm(process_name) in _PROTECTED


def allowed_in_dev_mode(process_name: str | None) -> bool:
    return _norm(process_name) in _DEV_ALLOWLIST


def is_panic_target(process_name: str | None) -> bool:
    return _norm(process_name) in _PANIC_TARGETS


def should_block(process_name: str | None, dev_mode: bool) -> bool:
    if not process_name:
        return False
    if is_protected(process_name):
        return False
    if dev_mode and allowed_in_dev_mode(process_name):
        return False
    return is_productive(process_name)
