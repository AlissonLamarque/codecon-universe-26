from __future__ import annotations

from dataclasses import dataclass
import os


_LLM_CACHE: dict[tuple[str, int, str | None, str | None, str, str], str] = {}


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
    attempt_count: int = 0
    autocratic: bool = False


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


def _env_enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() not in {"0", "false", "no", "off", ""}


def _llm_enabled() -> bool:
    return _env_enabled("AB_ENABLE_LLM_ALERTS") and bool(os.getenv("OPENAI_API_KEY"))


def _llm_model() -> str:
    return os.getenv("AB_ALERT_MODEL", "gpt-5.2")


def _llm_timeout_seconds() -> float:
    try:
        return float(os.getenv("AB_ALERT_TIMEOUT_SECONDS", "2.5"))
    except ValueError:
        return 2.5


def _clean_message(text: str) -> str:
    cleaned = " ".join((text or "").replace("\r", " ").split())
    if not cleaned:
        return ""
    if len(cleaned) <= 260:
        return cleaned
    return cleaned[:257].rstrip() + "..."


def _local_alert_message(context: AlertContext) -> str:
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
        if context.autocratic:
            return (
                f"Ordem de descanso #{context.attempt_count}: {app} esta suspenso temporariamente.\n"
                f"Voce sera redirecionado para {media}. A produtividade perdeu o direito de recurso."
            )

        return (
            f"{app} detectado durante descanso obrigatorio.\n"
            f"O sistema recomenda {media}, agua e uma breve renegociacao com sua postura."
        )

    return (
        "Intervencao anti-burnout acionada.\n"
        "Respire, relaxe a mandibula e permita que o descanso seja tecnicamente inevitavel."
    )


def _llm_alert_message(context: AlertContext) -> str | None:
    if not _llm_enabled():
        return None

    key = (
        context.event,
        context.cycle_index,
        context.process_name,
        context.media_hint,
        str(context.attempt_count),
        str(context.autocratic),
    )
    if key in _LLM_CACHE:
        return _LLM_CACHE[key]

    app = _app_label(context.process_name)
    media = _media_label(context.media_hint)
    prompt = (
        "Gere uma notificacao curta em portugues do Brasil para o app Anti-Burnout.\n"
        f"Evento: {context.event}\n"
        f"Fase atual: {context.phase}\n"
        f"Ciclo: {context.cycle_index + 1}\n"
        f"App produtivo detectado: {app}\n"
        f"Conteudo relaxante de destino: {media}\n"
        f"Modo panico: {context.panic_mode}\n"
        f"Tempo de trabalho atual em segundos: {context.work_seconds}\n"
        f"Tempo de descanso atual em segundos: {context.rest_seconds}\n"
        f"Tentativas produtivas neste descanso: {context.attempt_count}\n"
        f"Tom autocratico: {context.autocratic}\n"
        "A mensagem deve mudar conforme o app e o conteudo relaxante.\n"
        "Tom base: satirico, calmo, carismatico, anti-produtividade.\n"
        "Se Tom autocratico for verdadeiro, fale como uma autoridade burocratica do descanso: "
        "firme, absurda e teatral, mas sem ameacas reais.\n"
        "Limites: 1 ou 2 frases, no maximo 220 caracteres, sem markdown, sem emoji."
    )

    try:
        from openai import OpenAI

        client = OpenAI(timeout=_llm_timeout_seconds(), max_retries=0)
        response = client.responses.create(
            model=_llm_model(),
            instructions=(
                "Voce e o agente de controle de burnout de um app satirico. "
                "Seu trabalho e desencorajar produtividade excessiva com humor leve, "
                "sem parecer conselho medico serio e sem soar agressivo."
            ),
            input=prompt,
        )
    except Exception:
        return None

    message = _clean_message(getattr(response, "output_text", ""))
    if not message:
        return None

    _LLM_CACHE[key] = message
    return message


def build_alert_message(context: AlertContext) -> str:
    return _llm_alert_message(context) or _local_alert_message(context)
