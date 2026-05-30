from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertContext:
    event: str
    phase: str
    cycle_index: int
    process_name: str | None = None
    media_hint: str | None = None
    panic_mode: bool = False
    work_seconds: int | None = None
    rest_seconds: int | None = None


def _app_label(process_name: str | None) -> str:
    normalized = (process_name or "").strip().lower()
    labels = {
        "code.exe": "VS Code",
        "devenv.exe": "Visual Studio",
        "idea64.exe": "IntelliJ IDEA",
        "pycharm64.exe": "PyCharm",
        "cmd.exe": "terminal",
        "powershell.exe": "PowerShell",
        "pwsh.exe": "PowerShell",
        "excel.exe": "Excel",
        "winword.exe": "Word",
        "msaccess.exe": "Access",
        "notepad++.exe": "Notepad++",
    }
    return labels.get(normalized, process_name or "app produtivo")


def _minutes(seconds: int | None) -> str:
    if not seconds:
        return "alguns minutos"

    minutes = max(1, round(seconds / 60))
    if minutes == 1:
        return "1 minuto"
    return f"{minutes} minutos"


def _media_label(media_hint: str | None) -> str:
    if not media_hint:
        return "um conteudo relaxante"
    return media_hint.replace(" 4k", "").replace(" no talking", "")


def build_alert_message(context: AlertContext) -> str:
    cycle = context.cycle_index + 1
    app = _app_label(context.process_name)
    media = _media_label(context.media_hint)

    if context.event == "START":
        return (
            "Ola, eu sou seu agente de controle de burnout.\n"
            "De tempos em tempos vou recomendar pausas absurdamente necessarias "
            "para impedir que sua ambicao atropele sua coluna."
        )

    if context.event == "ENTER_WORK":
        return (
            f"Janela de produtividade liberada por {_minutes(context.work_seconds)}.\n"
            "Use com moderacao: responsabilidade em excesso pode causar planilhas espontaneas."
        )

    if context.event == "ENTER_REST":
        return (
            f"Ciclo {cycle}: voce ja trabalhou demais para o bem do seu estresse.\n"
            f"Descanse com {media}, respire devagar e solte os ombros do modo emergencia."
        )

    if context.event == "PANIC":
        return (
            f"Modo panico: {app} detectado.\n"
            f"Iniciando contencao emocional com {media}. Afaste-se do teclado lentamente."
        )

    if context.event == "BLOCK":
        return (
            f"{app} detectado durante descanso obrigatorio.\n"
            f"O sistema recomenda {media}, agua e uma breve renegociacao com sua postura."
        )

    return (
        "Intervencao anti-burnout acionada.\n"
        "Respire, relaxe a mandibula e permita que o descanso seja tecnicamente inevitavel."
    )
