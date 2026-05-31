from __future__ import annotations

from typing import Callable

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from app_state import AppState


def _format_time(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def _status_text(state: AppState) -> str:
    snap = state.snapshot()
    mode = "PAUSADO" if not snap["enabled"] else "ATIVO"
    phase = "DESCANSO" if snap["phase"] == "REST_FORCED" else "PRODUTIVIDADE"
    remaining = _format_time(snap["phase_remaining"])
    total = _format_time(snap["phase_total"])
    return f"{mode} | {phase} | {remaining}/{total} | ciclo {snap['cycle_index'] + 1}"


def _rest_work_text(state: AppState) -> str:
    snap = state.snapshot()
    rest = _format_time(snap["rest_seconds_current"])
    extra = _format_time(snap.get("rest_extension_seconds", 0))
    work = _format_time(snap["work_seconds_current"])
    return f"Descanso {rest} (+{extra}) | Trabalho {work}"


def _modes_text(state: AppState) -> str:
    snap = state.snapshot()
    dev = "ON" if snap["dev_mode"] else "OFF"
    panic = "ON" if snap["panic_mode"] else "OFF"
    notifications = "ON" if snap["overlay_enabled"] else "OFF"
    backend = str(snap.get("last_alert_backend", "local") or "local").strip().upper()
    return (
        f"Modo dev: {dev} | Modo panico: {panic} | Notificacoes: {notifications} | "
        f"Backend alerta: {backend}"
    )


def _create_icon_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill="#e11d48")
    draw.text((18, 18), "AB", fill="white")
    return img


def build_tray(
    state: AppState,
    on_toggle: Callable[[], None],
    on_toggle_dev_mode: Callable[[], None],
    on_toggle_panic_mode: Callable[[], None],
    on_toggle_overlay_mode: Callable[[], None],
    on_quit: Callable[[], None],
) -> Icon:
    def _on_toggle(icon: Icon, item: MenuItem) -> None:
        on_toggle()
        icon.update_menu()

    def _on_toggle_dev(icon: Icon, item: MenuItem) -> None:
        on_toggle_dev_mode()
        icon.update_menu()

    def _on_toggle_panic(icon: Icon, item: MenuItem) -> None:
        on_toggle_panic_mode()
        icon.update_menu()

    def _on_toggle_overlay(icon: Icon, item: MenuItem) -> None:
        on_toggle_overlay_mode()
        icon.update_menu()

    def _on_quit(icon: Icon, item: MenuItem) -> None:
        on_quit()
        icon.stop()

    menu = Menu(
        MenuItem(lambda item: _status_text(state), lambda icon, item: None, enabled=False),
        MenuItem(lambda item: _rest_work_text(state), lambda icon, item: None, enabled=False),
        MenuItem(lambda item: _modes_text(state), lambda icon, item: None, enabled=False),
        MenuItem(
            "Ativo",
            _on_toggle,
            checked=lambda item: state.snapshot()["enabled"],
        ),
        MenuItem(
            lambda item: f"Modo dev (nao bloqueia VSCode): {'ON' if state.snapshot()['dev_mode'] else 'OFF'}",
            _on_toggle_dev,
            checked=lambda item: state.snapshot()["dev_mode"],
        ),
        MenuItem(
            "Modo panico (forcar video no VSCode)",
            _on_toggle_panic,
            checked=lambda item: state.snapshot()["panic_mode"],
        ),
        MenuItem(
            "Notificacoes",
            _on_toggle_overlay,
            checked=lambda item: state.snapshot()["overlay_enabled"],
        ),
        MenuItem("Sair", _on_quit),
    )
    return Icon("anti_burnout", _create_icon_image(), "Anti-Burnout", menu)
