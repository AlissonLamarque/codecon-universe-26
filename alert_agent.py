from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_LLM_CACHE: dict[tuple[object, ...], str] = {}


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
    return _env_enabled("AB_ENABLE_LLM_ALERTS")


def _backend_mode() -> str:
    mode = os.getenv("AB_ALERT_BACKEND", "auto").strip().lower()
    if mode in {"auto", "ollama", "openai", "local"}:
        return mode
    return "auto"


def _openai_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _llm_model() -> str:
    return os.getenv("AB_ALERT_MODEL", "gpt-5.2")


def _llm_timeout_seconds() -> float:
    try:
        return float(os.getenv("AB_ALERT_TIMEOUT_SECONDS", "2.5"))
    except ValueError:
        return 2.5


def _ollama_enabled() -> bool:
    return _env_enabled("AB_ENABLE_OLLAMA_ALERTS", "1") and bool(_ollama_model())


def _ollama_model() -> str:
    return os.getenv("AB_OLLAMA_MODEL", "qwen2.5:1.5b-instruct")


def _ollama_base_url() -> str:
    return os.getenv("AB_OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")


def _ollama_timeout_seconds() -> float:
    try:
        return float(os.getenv("AB_OLLAMA_TIMEOUT_SECONDS", "2.2"))
    except ValueError:
        return 2.2


def _ollama_keep_alive() -> str:
    return os.getenv("AB_OLLAMA_KEEP_ALIVE", "10m")


def _llm_system_instructions() -> str:
    return (
        "Voce e o agente de controle de burnout de um app satirico. "
        "Seu trabalho e desencorajar produtividade excessiva com humor leve, "
        "sem parecer conselho medico serio e sem soar agressivo."
    )


def _build_alert_prompt(context: AlertContext) -> str:
    app = _app_label(context.process_name)
    media = _media_label(context.media_hint)
    return (
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
        attempt = max(1, context.attempt_count)
        if attempt == 1:
            return (
                f"{app} detectado durante descanso obrigatorio.\n"
                f"Voce ta produtivo demais. Bora relaxar com {media} por um momento."
            )
        if attempt == 2:
            return (
                "PARA de querer produzir, seu macaco do commit.\n"
                f"Volte para {media} e finja tranquilidade por alguns instantes."
            )
        return (
            f"Ordem de descanso #{attempt}: insistencia produtiva detectada em {app}.\n"
            f"{media} foi reaberto. A produtividade perdeu o direito de recurso."
        )

    if context.event == "RELAX_ESCAPE":
        attempt = max(1, context.attempt_count)
        if attempt == 1:
            return (
                "Tentativa de fuga detectada: essa nao e a janela oficial do descanso.\n"
                f"Retornando para {media}."
            )
        if attempt == 2:
            return (
                "Trocar de aba nao conta como descanso, colega.\n"
                f"Volte para {media} e respire antes de outra tentativa."
            )
        return (
            f"Protocolo anti-gambiarra #{attempt} ativado.\n"
            "PARA de querer produzir e volte para a janela de relax agora."
        )

    return (
        "Intervencao anti-burnout acionada.\n"
        "Respire, relaxe a mandibula e permita que o descanso seja tecnicamente inevitavel."
    )


def _openai_alert_message(prompt: str) -> str | None:
    if not _openai_enabled():
        return None

    try:
        from openai import OpenAI

        client = OpenAI(timeout=_llm_timeout_seconds(), max_retries=0)
        response = client.responses.create(
            model=_llm_model(),
            instructions=_llm_system_instructions(),
            input=prompt,
        )
    except Exception:
        return None

    message = _clean_message(getattr(response, "output_text", ""))
    if not message:
        return None
    return message


def _ollama_alert_message(prompt: str) -> str | None:
    if not _ollama_enabled():
        return None

    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "system": _llm_system_instructions(),
        "stream": False,
        "keep_alive": _ollama_keep_alive(),
        "options": {
            "temperature": 0.9,
            "num_predict": 90,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    url = f"{_ollama_base_url()}/api/generate"
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(request, timeout=_ollama_timeout_seconds()) as response:
            raw = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    except Exception:
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict) and parsed.get("error"):
        return None

    message = _clean_message(str(parsed.get("response", "")) if isinstance(parsed, dict) else "")
    if not message:
        return None
    return message


def _backend_order() -> list[str]:
    mode = _backend_mode()
    if mode == "local":
        return []
    if mode == "openai":
        return ["openai"]
    if mode == "ollama":
        return ["ollama"]
    return ["ollama", "openai"]


def _llm_alert_message(context: AlertContext) -> str | None:
    if not _llm_enabled():
        return None

    mode = _backend_mode()
    key = (
        mode,
        context.event,
        context.cycle_index,
        context.process_name,
        context.media_hint,
        str(context.attempt_count),
        str(context.autocratic),
    )
    if key in _LLM_CACHE:
        return _LLM_CACHE[key]

    prompt = _build_alert_prompt(context)

    generated: str | None = None
    for backend in _backend_order():
        if backend == "ollama":
            generated = _ollama_alert_message(prompt)
        elif backend == "openai":
            generated = _openai_alert_message(prompt)
        else:
            generated = None

        if generated:
            break

    if not generated:
        return None

    _LLM_CACHE[key] = generated
    return generated


def build_alert_message(context: AlertContext) -> str:
    return _llm_alert_message(context) or _local_alert_message(context)
