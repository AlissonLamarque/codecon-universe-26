from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_LLM_CACHE: dict[tuple[object, ...], tuple[str, str]] = {}
_LAST_ALERT_BACKEND = "local"
_ALERT_LOCK = threading.Lock()


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
        return "video de relax"

    lowered = media_hint.strip().lower()
    if any(token in lowered for token in ("shitpost", "brainrot", "meme", "dopamina", "chaos", "caos")):
        return "video meme caotico"
    if any(token in lowered for token in ("satisfying", "slime", "sand", "kinetic")):
        return "video satisfying"
    if any(token in lowered for token in ("ambiente", "calmante", "lofi", "fireplace")):
        return "video calmante"
    if any(token in lowered for token in ("atual", "andamento", "ja aberto", "mesmo video")):
        return "video de relax atual"
    if any(token in lowered for token in ("ocean", "wave", "mar")):
        return "video de mar"
    if any(token in lowered for token in ("forest", "bird", "floresta")):
        return "video de floresta"
    if any(token in lowered for token in ("waterfall", "cachoeira")):
        return "video de cachoeira"
    if any(token in lowered for token in ("rain", "chuva")):
        return "video de chuva"
    if any(token in lowered for token in ("nature", "natureza", "scenery")):
        return "video de natureza"

    return "video de relax"


def _media_reason_options(media_hint: str | None) -> list[str]:
    lowered = (media_hint or "").strip().lower()
    if any(token in lowered for token in ("shitpost", "brainrot", "meme", "dopamina", "chaos", "caos")):
        return [
            "choque de dopamina corta tua obsessao produtiva",
            "caos meme interrompe teu loop de produtividade",
            "FORCAR DOPAMINA agora te tira do modo burnout",
        ]
    if any(token in lowered for token in ("satisfying", "slime", "sand", "kinetic")):
        return [
            "satisfying visual reseta teu foco compulsivo",
            "estimulo visual curto quebra teu pico de ansiedade",
            "padroes repetitivos acalmam teu sistema em sobrecarga",
        ]
    if any(token in lowered for token in ("ambiente", "calmante", "lofi", "fireplace")):
        return [
            "ambiente calmo reduz tua pressa de produzir tudo",
            "som continuo estabiliza tua cabeca acelerada",
            "clima tranquilo baixa teu estresse operacional",
        ]
    if any(token in lowered for token in ("atual", "andamento", "ja aberto", "mesmo video")):
        return [
            "continuar no mesmo video evita recaida produtiva",
            "manter essa aba evita teu retorno pro modo planilha",
            "voltar pro mesmo video impede reaquecer o foco produtivo",
        ]
    if any(token in lowered for token in ("ocean", "wave", "mar")):
        return [
            "som de mar desacelera tua mente",
            "ondas tiram tua cabeca do modo sprint",
            "barulho do oceano baixa teu giro mental",
        ]
    if any(token in lowered for token in ("forest", "bird", "floresta")):
        return [
            "sons de floresta aliviam tensao mental",
            "passarinhos reduzem tua vontade de planilhar tudo",
            "ambiente de mata desliga teu modo tarefa infinita",
        ]
    if any(token in lowered for token in ("waterfall", "cachoeira")):
        return [
            "agua correndo quebra teu loop de estresse",
            "cachoeira limpa o ruido da tua cabeca",
            "som de agua corta teu ciclo de ansiedade produtiva",
        ]
    if any(token in lowered for token in ("rain", "chuva")):
        return [
            "chuva baixa ansiedade de produzir sem parar",
            "som de chuva te tira do modo pressa eterna",
            "chuva ajuda a desacoplar teu cerebro do trabalho",
        ]
    if any(token in lowered for token in ("nature", "natureza", "scenery")):
        return [
            "natureza desliga teu modo overclock",
            "cena natural reduz teu fogo de produtividade",
            "paisagem calma puxa teu sistema pra modo humano",
        ]
    return [
        "pausa guiada evita mini-burnout",
        "descanso curto protege teu cerebro do modo fritacao",
        "intervalo forcado evita que tu vire uma planilha viva",
    ]


def _media_reason_options_local(media_hint: str | None) -> list[str]:
    lowered = (media_hint or "").strip().lower()
    if any(token in lowered for token in ("shitpost", "brainrot", "meme", "dopamina", "chaos", "caos")):
        return [
            "choque de dopamina corta tua obsessao produtiva",
            "caos meme interrompe teu loop de produtividade",
            "FORCAR DOPAMINA agora te tira do modo burnout",
            "brainrot controlado quebra teu modo trabalho infinito",
            "estimulo idiota rouba tua atencao da planilha mental",
            "meme barulhento interrompe teu piloto automatico de tarefa",
        ]
    if any(token in lowered for token in ("satisfying", "slime", "sand", "kinetic")):
        return [
            "satisfying visual reseta teu foco compulsivo",
            "estimulo visual curto quebra teu pico de ansiedade",
            "padroes repetitivos acalmam teu sistema em sobrecarga",
            "video hipnotico desacopla tua cabeca do modo entrega",
            "movimento repetitivo reduz tua pressa de resolver tudo",
            "textura visual besta serve de freio pro teu overclock",
        ]
    if any(token in lowered for token in ("ambiente", "calmante", "lofi", "fireplace")):
        return [
            "ambiente calmo reduz tua pressa de produzir tudo",
            "som continuo estabiliza tua cabeca acelerada",
            "clima tranquilo baixa teu estresse operacional",
            "ambiente de fundo desacelera tua mente em espiral",
            "paisagem calma evita tua recaida em multitarefa",
            "som neutro derruba tua febre de produtividade",
        ]
    if any(token in lowered for token in ("atual", "andamento", "ja aberto", "mesmo video")):
        return [
            "continuar no mesmo video evita recaida produtiva",
            "manter essa aba evita teu retorno pro modo planilha",
            "voltar pro mesmo video impede reaquecer o foco produtivo",
            "ficar no video atual corta tua vontade de voltar ao codigo",
            "seguir no mesmo clip reduz tentacao de alt-tab produtivo",
            "persistir nessa janela segura teu descanso obrigatorio",
        ]
    if any(token in lowered for token in ("ocean", "wave", "mar")):
        return [
            "som de mar desacelera tua mente",
            "ondas tiram tua cabeca do modo sprint",
            "barulho do oceano baixa teu giro mental",
            "mar constante desarma teu modo urgencia",
            "ondas em loop ajudam tua mente a largar o teclado",
            "oceano em fundo continuo derruba teu ritmo de corrida",
        ]
    if any(token in lowered for token in ("forest", "bird", "floresta")):
        return [
            "sons de floresta aliviam tensao mental",
            "passarinhos reduzem tua vontade de planilhar tudo",
            "ambiente de mata desliga teu modo tarefa infinita",
            "canto de aves puxa tua cabeca para ritmo humano",
            "floresta em loop corta tua compulsao de produtividade",
            "sons naturais reduzem tua pressa de entregar tudo hoje",
        ]
    if any(token in lowered for token in ("waterfall", "cachoeira")):
        return [
            "agua correndo quebra teu loop de estresse",
            "cachoeira limpa o ruido da tua cabeca",
            "som de agua corta teu ciclo de ansiedade produtiva",
            "fluxo continuo de agua desacopla tua mente do sprint",
            "cachoeira em loop esfria teu processador mental",
            "barulho de agua tira teu foco da pressao de entrega",
        ]
    if any(token in lowered for token in ("rain", "chuva")):
        return [
            "chuva baixa ansiedade de produzir sem parar",
            "som de chuva te tira do modo pressa eterna",
            "chuva ajuda a desacoplar teu cerebro do trabalho",
            "pingos constantes diminuem teu impulso de abrir tarefa",
            "chuva longa reduz teu ritmo de correria mental",
            "som chuvoso segura tua vontade de voltar pro codigo",
        ]
    if any(token in lowered for token in ("nature", "natureza", "scenery")):
        return [
            "natureza desliga teu modo overclock",
            "cena natural reduz teu fogo de produtividade",
            "paisagem calma puxa teu sistema pra modo humano",
            "natureza em tela cheia derruba tua urgencia artificial",
            "paisagem ampla reduz tua ansiedade de resolver tudo",
            "video natural ajuda tua mente a voltar pro eixo",
        ]
    return [
        "pausa guiada evita mini-burnout",
        "descanso curto protege teu cerebro do modo fritacao",
        "intervalo forcado evita que tu vire uma planilha viva",
        "pausa obrigatoria segura teu foco compulsivo",
        "respiro tecnico evita tua escalada de cansaco",
        "descanso rapido protege tua atencao de colapso",
    ]


def _media_reason(media_hint: str | None) -> str:
    return _media_reason_options_local(media_hint)[0]


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


def _ollama_num_predict() -> int:
    try:
        value = int(os.getenv("AB_OLLAMA_NUM_PREDICT", "45"))
    except ValueError:
        return 45
    return max(20, min(90, value))


def _llm_max_chars() -> int:
    try:
        value = int(os.getenv("AB_ALERT_MAX_CHARS", "170"))
    except ValueError:
        return 170
    return max(80, min(280, value))


def _llm_system_instructions() -> str:
    return (
        "Voce e o agente anti-burnout de um app satirico. "
        "Seu trabalho e cortar produtividade durante descanso com humor brasileiro curto e direto. "
        "Escreva espontaneo, com leve zoeira, sem parecer texto formal. "
        "Nao use tom medico serio e nao passe de agressividade leve. "
        "Escreva em portugues do Brasil. "
        "Proibido usar linguagem de RPG, tribunal, protocolo, escalada numerada ou codinomes. "
        "Nunca use hashtags, colchetes, markdown, emoji, texto em ingles ou simbolos estranhos."
    )


def _irritation_level(context: AlertContext) -> int:
    attempt = max(0, context.attempt_count)
    if context.event == "PANIC":
        return max(4, attempt + 2)
    if context.event not in {"BLOCK", "RELAX_ESCAPE"}:
        return 1
    return max(1, attempt)


def _irritation_label(level: int) -> str:
    if level <= 1:
        return "de boa"
    if level == 2:
        return "impaciente leve"
    if level <= 4:
        return "impaciente"
    if level <= 7:
        return "sem paciencia"
    if level <= 12:
        return "pouca paciencia"
    if level <= 20:
        return "muito puto"
    return "puto maximo"


def _build_alert_prompt(context: AlertContext) -> str:
    app = _app_label(context.process_name)
    media = _media_label(context.media_hint)
    media_reason = _media_reason(context.media_hint)
    max_chars = _llm_max_chars()
    irritation_level = _irritation_level(context)
    irritation_label = _irritation_label(irritation_level)
    event_style = (
        "Intervencao durante descanso: bloquear app produtivo e mandar relaxar."
        if context.event in {"BLOCK", "RELAX_ESCAPE", "PANIC"}
        else "Mensagem curta de sistema anti-burnout."
    )
    return (
        "Gere uma notificacao curta em portugues do Brasil para o app Anti-Burnout.\n"
        f"Evento: {context.event}\n"
        f"Estilo do evento: {event_style}\n"
        f"Fase atual: {context.phase}\n"
        f"Ciclo: {context.cycle_index + 1}\n"
        f"App produtivo detectado: {app}\n"
        f"Conteudo relaxante de destino: {media}\n"
        f"Modo panico: {context.panic_mode}\n"
        f"Tempo de trabalho atual em segundos: {context.work_seconds}\n"
        f"Tempo de descanso atual em segundos: {context.rest_seconds}\n"
        f"Tentativas produtivas neste descanso: {context.attempt_count}\n"
        f"Nivel de irritacao requerido: {irritation_level} ({irritation_label})\n"
        f"Tom autocratico: {context.autocratic}\n"
        "Tema obrigatorio: prevencao de burnout e freio em produtividade excessiva.\n"
        f"Motivo tecnico-humoristico do conteudo relaxante: {media_reason}.\n"
        "A mensagem deve mudar conforme o app e o conteudo relaxante.\n"
        "Tom base: satirico, engracado e anti-produtividade.\n"
        "Se Tom autocratico for verdadeiro, seja mais firme e impaciente, sem personagem cringe.\n"
        "Progressao de irritacao obrigatoria e sem teto:\n"
        "- Quanto maior o nivel, mais direto e sem paciencia voce fica.\n"
        "- Niveis altos devem soar como bronca memeira, sem delirio de lore.\n"
        "- Nunca reduza o tom quando o nivel aumentar.\n"
        f"- O nivel atual e {irritation_level}; siga esse nivel exatamente.\n"
        f"Limites: 1 frase so, no maximo {max_chars} caracteres, "
        "entre 7 e 14 palavras, sem markdown, sem emoji, sem texto formal.\n"
        "Proibido: ingles, hashtags, colchetes, asteriscos, lista, codigo.\n"
        "Nao use palavras tipo escalada, tentativa numerada, protocolo, tribunal, nivel X.\n"
        "Inclua justificativa curta do relax, no estilo 'porque ...'.\n"
        "Nunca use codinomes, sufixos de nivel ou siglas aleatorias.\n"
        "Exemplos de estilo bom:\n"
        f"- '{app} de novo? fecha isso e vai pro {media}, porque tu precisa baixar giro.'\n"
        f"- 'Sem produtividade agora: te joguei no {media}, porque teu cerebro ta no limite.'\n"
        "- 'Volta pro relax agora, porque insistir nisso ai e pedir burnout parcelado.'"
    )


def _clean_message(text: str) -> str:
    raw = (text or "").replace("\r", " ").replace("\n", " ")
    raw = raw.replace("\u201c", "\"").replace("\u201d", "\"").replace("\u2019", "'").replace("\u2014", "-").replace("\u2013", "-")
    cleaned = " ".join(raw.split())
    if not cleaned:
        return ""

    # Trim noisy wrapping quotes generated by some local models.
    cleaned = cleaned.strip().strip("\"'`")
    cleaned = cleaned.strip()
    if not cleaned:
        return ""

    # Remove common noisy fragments from smaller local models.
    cleaned = re.sub(r"[\"']\s*-\s*[\"']\s*", " ", cleaned)
    cleaned = re.sub(r"\s+-\s+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # Keep only complete sentences when possible to drop broken tails.
    sentence_parts = re.findall(r"[^.!?]+[.!?]", cleaned)
    if sentence_parts:
        normalized_sentences: list[str] = []
        for part in sentence_parts:
            s = " ".join(part.split()).strip().strip("\"'`- ")
            if not s:
                continue
            letters = [ch for ch in s if ch.isalpha()]
            if len(letters) < 10:
                continue
            normalized_sentences.append(s)
        if normalized_sentences:
            cleaned = " ".join(normalized_sentences[:2]).strip()

    cleaned = cleaned.strip().strip("\"'`- ").strip()
    if not cleaned:
        return ""

    # Final character clamp for quick 4s reading.
    max_chars = _llm_max_chars()
    if len(cleaned) > max_chars:
        clipped = cleaned[:max_chars].rstrip()
        if " " in clipped:
            clipped = clipped.rsplit(" ", 1)[0].rstrip()
        cleaned = clipped or cleaned[:max_chars].rstrip()

    return cleaned


def _is_low_quality_llm_message(message: str) -> bool:
    msg = (message or "").strip()
    if not msg:
        return True

    if len(msg) < 24:
        return True

    if any(ch in msg for ch in ("[", "]", "{", "}", "#", "*", "|", "`")):
        return True

    words = msg.split()
    if len(words) < 5:
        return True

    letters = [ch for ch in msg if ch.isalpha()]
    if len(letters) < 18:
        return True

    upper_count = sum(1 for ch in letters if ch.isupper())
    if upper_count >= max(6, int(len(letters) * 0.55)):
        return True

    if msg.endswith("..."):
        return True
    if msg.endswith(":"):
        return True
    if msg.count("\"") % 2 == 1:
        return True

    if re.search(r"\b(block|relax_escape|panic|start|enter_rest|enter_work|rest_forced|productive_window)\b", msg, flags=re.IGNORECASE):
        return True
    if re.search(r"\brest\s*forc", msg, flags=re.IGNORECASE):
        return True
    if re.search(r"\bvsc\s*code\b", msg, flags=re.IGNORECASE):
        return True

    if "_" in msg:
        return True
    if re.search(r"\bporque\s+precisamos\s+de\s*$", msg, flags=re.IGNORECASE):
        return True
    if re.search(r"[\"']\s*-\s*", msg):
        return True

    return False


def _strip_technical_prefix(message: str) -> str:
    msg = _clean_message(message)
    if not msg:
        return ""

    patterns = [
        r"^(?:\b(?:block|relax_escape|panic|start|enter_rest|enter_work|rest_forced|productive_window)\b[!:\s._-]*)+",
        r"^(?:evento|evento atual|fase|status)\s*[:=-]\s*",
    ]
    for pattern in patterns:
        msg = re.sub(pattern, "", msg, flags=re.IGNORECASE).lstrip(" .:-")

    return msg.strip()


def _tokenize_keywords(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    stopwords = {
        "de",
        "do",
        "da",
        "dos",
        "das",
        "e",
        "a",
        "o",
        "um",
        "uma",
        "para",
        "por",
        "com",
        "no",
        "na",
        "nos",
        "nas",
        "to",
        "ta",
    }
    return [tok for tok in raw_tokens if len(tok) >= 3 and tok not in stopwords]


def _is_contextual_llm_message(context: AlertContext, message: str) -> bool:
    msg = (message or "").strip().lower()
    if not msg:
        return False

    if re.search(r"\b(escalada|tentativa|protocolo|tribunal)\b", msg):
        return False
    if re.search(r"\bnivel\s*\d+\b", msg):
        return False
    if re.search(r"\b[a-z]+-e\d+\b", msg):
        return False
    if re.search(r"\b(block|relax_escape|rest_forced|productive_window|enter_rest|enter_work)\b", msg):
        return False
    if re.search(r"\brest\s*forc", msg):
        return False
    if re.search(r"\bvsc\s*code\b", msg):
        return False

    if context.event not in {"BLOCK", "RELAX_ESCAPE", "PANIC"}:
        return True

    # Must sound like an intervention command, not random chat.
    command_words = {
        "volta",
        "retorna",
        "larga",
        "fecha",
        "descansa",
        "relax",
        "pausa",
        "respira",
        "foco",
        "agora",
    }
    if not any(word in msg for word in command_words):
        return False

    burnout_words = {
        "burnout",
        "descanso",
        "relax",
        "pausa",
        "produtiv",
        "teimos",
        "descansa",
        "respira",
    }
    if not any(word in msg for word in burnout_words):
        return False

    if context.event in {"BLOCK", "RELAX_ESCAPE", "PANIC"} and ("porque" not in msg and "pra " not in msg):
        return False

    # Must mention either productive app context or relax media context.
    app_tokens = _tokenize_keywords(_app_label(context.process_name))
    media_tokens = _tokenize_keywords(_media_label(context.media_hint))
    has_app_hint = any(tok in msg for tok in app_tokens)
    has_media_hint = any(tok in msg for tok in media_tokens)
    if not (has_app_hint or has_media_hint):
        return False

    return True


def _stable_index(seed: str, size: int) -> int:
    if size <= 1:
        return 0
    total = 0
    for idx, ch in enumerate(seed):
        total += (idx + 1) * ord(ch)
    return total % size


def _pick_variant(context: AlertContext, tag: str, options: list[str]) -> str:
    size = len(options)
    base_seed = f"{context.event}|{context.cycle_index}|{context.process_name}|{context.media_hint}|{tag}"
    base = _stable_index(base_seed, size)
    step = max(0, context.attempt_count)
    return options[(base + step) % size]


def _local_max_chars() -> int:
    try:
        value = int(os.getenv("AB_LOCAL_ALERT_MAX_CHARS", "165"))
    except ValueError:
        return 165
    return max(120, min(260, value))


def _finalize_local_message(text: str) -> str:
    raw = " ".join((text or "").replace("\r", " ").replace("\n", " ").split())
    if not raw:
        return "Intervencao anti-burnout acionada: pausa obrigatoria em andamento."

    raw = raw.replace(" ;", ";").replace(" ,", ",").replace(" .", ".")
    raw = re.sub(r"\s*([,;:.!?])\s*", r"\1 ", raw).strip()
    raw = re.sub(r"\s{2,}", " ", raw).strip()

    limit = _local_max_chars()
    if len(raw) > limit:
        clipped = raw[:limit].rstrip()
        if " " in clipped:
            clipped = clipped.rsplit(" ", 1)[0].rstrip()
        raw = clipped.rstrip(" ,;:-")

    if not raw.endswith((".", "!", "?")):
        raw += "."

    return raw


def _build_combo_message(
    context: AlertContext,
    tag: str,
    *,
    openers: list[str],
    actions: list[str],
    reasons: list[str],
    closers: list[str],
) -> str:
    opener = _pick_variant(context, f"{tag}_opener", openers)
    action = _pick_variant(context, f"{tag}_action", actions)
    reason = _pick_variant(context, f"{tag}_reason", reasons)
    closer = _pick_variant(context, f"{tag}_closer", closers)

    limit = _local_max_chars()
    candidates = [
        f"{opener}; {action}; {reason}; {closer}",
        f"{opener}; {action}; {reason}",
        f"{action}; {reason}; {closer}",
        f"{action}; {reason}",
        f"{opener}; {action}",
        action,
    ]

    reason_head = reason.split(",")[0].split(" e ", 1)[0].strip()
    if reason_head and reason_head != reason:
        candidates.insert(2, f"{opener}; {action}; {reason_head}")
        candidates.insert(4, f"{action}; {reason_head}")

    for candidate in candidates:
        normalized = " ".join(candidate.split())
        if len(normalized) <= limit:
            return _finalize_local_message(normalized)

    return _finalize_local_message(candidates[0])


def _attempt_tone(attempt: int) -> str:
    if attempt <= 2:
        return "light"
    if attempt <= 5:
        return "firm"
    if attempt <= 9:
        return "hard"
    if attempt <= 14:
        return "rage"
    return "chaos"


def _local_alert_message(context: AlertContext) -> str:
    cycle = context.cycle_index + 1
    app = _app_label(context.process_name)
    media = _media_label(context.media_hint)
    media_reason = _pick_variant(context, "media_reason", _media_reason_options_local(context.media_hint))
    attempt = max(1, context.attempt_count)
    tone = _attempt_tone(attempt)

    reason_clauses = [
        f"porque {media_reason}",
        "porque tu precisa baixar giro agora",
        "porque insistir nisso vira burnout parcelado",
        "porque tua cabeca ja estava em overclock",
        "porque pausa obrigatoria evita foco podre depois",
        "porque descanso curto preserva tua energia mental",
        "porque teu ritmo tava subindo mais que o saudavel",
        "porque sem pausa tu entra em modo zumbi de teclado",
    ]

    if context.event == "START":
        options = [
            "Sistema anti-burnout ligado: produtividade sem pausa virou atividade de risco.",
            "Agente de descanso ativo: se tu forcar muito, eu corto teu embalo.",
            "Modo preservacao mental iniciado: hoje teu cerebro nao vira churrasqueira.",
            "Anti-burnout online: meu trabalho e impedir tua produtividade compulsiva.",
            "Modo anti-fritacao ativado: se exagerar no foco, eu puxo teu freio.",
            "Descanso inteligente iniciou: produtividade compulsiva sera gentilmente sabotada.",
            "Monitor de sobrecarga ligado: produzir sem pausa nao passa mais batido.",
            "Guarda anti-burnout em servico: teu overclock mental esta sob vigilancia.",
            "Protecao cognitiva online: eu travo tua correria antes do colapso.",
            "Motor de pausa iniciou: hoje o teclado nao vai ganhar de ti.",
            "Supervisor de descanso ativo: teu foco agora tem limite de seguranca.",
            "Escudo mental em execucao: produtividade sem freio foi oficialmente barrada.",
            "Sistema de anti-exaustao iniciou: correr demais agora da intervencao.",
            "Fiscal de pausa na area: teu cerebro nao vira usina hoje.",
        ]
        return _finalize_local_message(_pick_variant(context, "start", options))

    if context.event == "ENTER_WORK":
        options = [
            f"Produtividade liberada por {_minutes(context.work_seconds)}; usa com responsabilidade.",
            f"Janela de trabalho aberta por {_minutes(context.work_seconds)}; sem speedrun de estresse.",
            f"Pode produzir por {_minutes(context.work_seconds)}, mas sem fritar o cortex.",
            f"Trabalho liberado por {_minutes(context.work_seconds)}; exagerou, eu volto.",
            f"Intervalo de producao aberto por {_minutes(context.work_seconds)}; sem maratona toxica.",
            f"Tu ganhou {_minutes(context.work_seconds)} de foco; usa sem transformar em caos.",
            f"Permissao de trabalho por {_minutes(context.work_seconds)}; ritmo humano, nao robo.",
            f"Janela produtiva de {_minutes(context.work_seconds)} liberada; sem sprint suicida.",
            f"Pode mexer no {app} por {_minutes(context.work_seconds)}; sem crise de urgencia.",
            f"Modo trabalho por {_minutes(context.work_seconds)}: entrega sim, autoexplosao nao.",
            f"Produtividade parcial ativada por {_minutes(context.work_seconds)}; sem overdrive.",
            f"Agora vale produzir por {_minutes(context.work_seconds)}; lembra de respirar entre tarefas.",
            f"Trabalho autorizado por {_minutes(context.work_seconds)}; se passar do ponto eu entro.",
            f"Rodada de foco por {_minutes(context.work_seconds)} iniciada; mantem o cerebro inteiro.",
        ]
        return _finalize_local_message(_pick_variant(context, "enter_work", options))

    if context.event == "ENTER_REST":
        return _build_combo_message(
            context,
            "enter_rest",
            openers=[
                f"Ciclo {cycle} entrou em descanso",
                "Pausa obrigatoria iniciada",
                "Troca de fase confirmada",
                "Modo relaxamento ativado",
                "Reset mental em andamento",
                "Intervalo anti-burnout iniciado",
                "Descanso oficial liberado",
                "Fase de baixar o giro iniciada",
                "Modo produtividade bloqueada entrou",
                "Janela de recuperacao cognitiva aberta",
            ],
            actions=[
                f"abri {media} pra segurar teu ritmo",
                f"te levei direto pro {media}",
                f"substitui tarefa por {media}",
                f"travei app produtivo e puxei {media}",
                f"redirecionei teu foco para {media}",
                f"te mantive fora do teclado com {media}",
                f"promovi transferencia imediata para {media}",
                f"deixei {media} na frente da tua correria",
                f"ativei {media} como bloqueio de overclock",
                f"te arrastei para {media} antes do surto de entrega",
            ],
            reasons=reason_clauses,
            closers=[
                "fica ai um pouco e deixa teu sistema baixar rotacao",
                "isso e manutencao preventiva do teu cerebro",
                "se insistir em produzir, eu repito a dose",
                "teu foco volta depois, sem fritar teu processador mental",
                "descansar agora evita retrabalho feito no modo exausto",
                "e um pit stop obrigatorio pra tu nao quebrar no meio",
                "usa essa pausa pra respirar e parar de correr contra o tempo",
                "teimosia aumenta intervencao, cooperacao libera mais rapido",
            ],
        )

    if context.event == "PANIC":
        return _build_combo_message(
            context,
            "panic",
            openers=[
                "Modo panico anti-burnout acionado",
                "Intervencao imediata confirmada",
                "Bloqueio urgente executado",
                "Resposta rapida de preservacao mental ativa",
                "Estado critico de teimosia detectado",
                "Acao de emergencia anti-sobrecarga disparada",
                "Freio de produtividade forcado iniciado",
                "Protocolo de descanso sem discussao entrou",
            ],
            actions=[
                f"tirei {app} da rota e enfiei {media}",
                f"pausei {app} e botei {media} na tua frente",
                f"minimizei {app} e priorizei {media}",
                f"interrompi {app} e redirecionei pro {media}",
                f"cancelei tua ofensiva produtiva com {media}",
                f"desviei teu foco direto para {media}",
                f"troquei tua tela para {media} sem votacao",
                f"cortei o atalho do {app} e mantive {media} dominante",
            ],
            reasons=reason_clauses,
            closers=[
                "agora segura a onda e descansa por bem",
                "insistir aqui so aumenta a firmeza do bloqueio",
                "teu cerebro pediu pausa, eu so executei",
                "isso e anti-burnout em tempo real",
                "quanto mais forca, mais eu puxo pro relax",
                "volta pro relax e evita extender esse sofrimento",
                "aceita a pausa e sai ganhando na proxima rodada",
                "descanso primeiro, produtividade depois",
            ],
        )

    if context.event == "BLOCK":
        if tone == "light":
            return _build_combo_message(
                context,
                "block_light",
                openers=[
                    "Opa, produtividade fora de hora",
                    "Calma ai, maratonista de entrega",
                    "Peguei tentativa antecipada de trabalho",
                    "Sinal amarelo de foco excessivo",
                    "Descanso ainda esta valendo",
                    "Tentativa de furar pausa detectada",
                    "Ei, sem speedrun de produtividade agora",
                    "Tua teimosia apareceu cedo hoje",
                ],
                actions=[
                    f"minimizei {app} e abri {media}",
                    f"te tirei do {app} e voltei pro {media}",
                    f"interrompi {app} e priorizei {media}",
                    f"bloqueei o atalho do {app} com {media}",
                    f"deixei {app} em espera e joguei {media} na frente",
                    f"redirecionei tua tela do {app} para {media}",
                    f"puxei teu foco do {app} para {media}",
                    f"cancelei a investida no {app} e reabri {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "coopera comigo que o trabalho volta logo",
                    "essa pausa e o cinto de seguranca do teu cerebro",
                    "respira e curte um minuto sem planilha",
                    "hoje eu sou teu freio de mao emocional",
                    "teu eu de daqui a duas horas vai agradecer",
                    "sem drama, e so manutencao preventiva",
                    "foco volta ja ja, cansaco nao precisa acumular",
                    "deixa eu fazer meu trabalho de te proteger de ti mesmo",
                ],
            )
        if tone == "firm":
            return _build_combo_message(
                context,
                "block_firm",
                openers=[
                    "Tu voltou cedo demais pro trampo",
                    "To vendo insistencia pra produzir fora de hora",
                    "Tu tentou acelerar de novo",
                    "La vem tu querendo furar a pausa",
                    "De novo essa tentativa de quebrar o descanso",
                    "Tu ta tentando trabalhar em horario bloqueado",
                    "Voltou pro teclado antes da hora",
                    "Nova escapada pro modo tarefeiro detectada",
                ],
                actions=[
                    f"{app} caiu pra segundo plano e {media} assumiu",
                    f"reabri {media} e afastei {app}",
                    f"troquei tua frente de trabalho por {media}",
                    f"travei retorno ao {app} e mantive {media}",
                    f"anulei teu alt-tab produtivo com {media}",
                    f"minimizei {app} e reforcei {media} na tela",
                    f"desativei tua corrida no {app} e mantive {media}",
                    f"bloqueei o impulso de codigo via {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "quanto mais teima, mais firme eu fico",
                    "descanso obrigatorio e nao opcional",
                    "seu foco esta bom, tua recuperacao tambem precisa estar",
                    "aceita o pit stop pra nao quebrar no proximo sprint",
                    "isso aqui e anti-burnout, nao anti-progresso",
                    "teimosia custa caro em energia mental",
                    "faz a pausa agora pra produzir melhor depois",
                    "na moral, protege esse cerebro ai",
                ],
            )
        if tone == "hard":
            return _build_combo_message(
                context,
                "block_hard",
                openers=[
                    "Ta bem claro que tu quer forcar a barra",
                    "Tu voltou pra produtividade de novo",
                    "Hoje tu acordou no modo teimoso mesmo",
                    "Tu ta tentando passar por cima do anti-burnout",
                    "La vem correria fora de hora outra vez",
                    "Teclado atacado em fase bloqueada de novo",
                    "Tentativa insistente, zero surpresa",
                    "Teu overclock mental ta querendo mandar em tudo",
                ],
                actions=[
                    f"{app} foi minimizado de novo e {media} voltou",
                    f"reancorei teu foco no {media} sem negociacao",
                    f"cortei o retorno ao {app} e mantive {media}",
                    f"remapeei tua atencao para {media} imediatamente",
                    f"encerrei a ofensiva produtiva com {media} em destaque",
                    f"desviei tua tela para {media} e segurei o bloqueio",
                    f"puxei teu foco pra longe do {app} com {media}",
                    f"interceptei tua corrida e reativei {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "tu nao vai perder nada por pausar dois minutos",
                    "isso evita aquela fadiga burra que destrui qualidade",
                    "descanso agora e performance depois",
                    "teu cerebro nao e servidor de alta disponibilidade",
                    "produzir exausto so gera retrabalho feio",
                    "se insistir, a intervencao escala sem pena",
                    "aceita o relax e economiza saude mental",
                    "calma o impulso de resolver o universo hoje",
                ],
            )
        if tone == "rage":
            return _build_combo_message(
                context,
                "block_rage",
                openers=[
                    "Ta forcando demais, chefe",
                    "Chega de tentativa de burlar pausa",
                    "Teimosia premium detectada",
                    "Tu realmente quer ganhar no cansaco hoje",
                    "A insistencia virou esporte olimpico",
                    "Nao era pra voltar pro modo trabalho agora",
                    "Segue tentando e eu sigo bloqueando",
                    "Sinal vermelho de sobrecarga acendeu geral",
                ],
                actions=[
                    f"arranquei {app} do foco e enfiei {media}",
                    f"bloqueei o {app} de novo e mantive {media}",
                    f"anulei tua retomada e reabri {media}",
                    f"recoloquei {media} na frente sem debate",
                    f"te puxei de volta pro {media} no seco",
                    f"tua aba produtiva foi neutralizada por {media}",
                    f"minimizei {app} e reinstalei {media} no comando",
                    f"te devolvi pro {media} com prioridade maxima",
                ],
                reasons=reason_clauses,
                closers=[
                    "nao testa minha paciencia computacional hoje",
                    "teimosia so alonga teu proprio descanso",
                    "eu prefiro ser chato agora do que te ver quebrado depois",
                    "aceita o relax e para de lutar contra o obvio",
                    "cansaco acumulado nao e medalha",
                    "teu modo heroi precisa de freio urgente",
                    "descansa e para de negociar com a exaustao",
                    "se insistir mais, a maluquice aumenta",
                ],
            )
        return _build_combo_message(
            context,
            "block_chaos",
            openers=[
                "Tu entrou no modo teimosia sem limite",
                "Agora virou loop: tu insiste e eu bloqueio",
                "Produtividade repetida ate o infinito",
                "Tu ta tentando vencer no cansaco",
                "Insistencia braba sem intervalo",
                "Tu ta tratando descanso como boss final",
                "Guerra contra a pausa foi pra fase final",
                "Auto-sabotagem produtiva no talo",
            ],
            actions=[
                f"{app} foi chutado pra escanteio e {media} segue reinando",
                f"intervencao total: sem {app}, so {media} no comando",
                f"retorno produtivo foi negado e {media} ficou fixo",
                f"travamento completo no {app}; destino oficial {media}",
                f"teu foco foi sequestrado de volta para {media}",
                f"bloqueio soberano ativo: {media} na frente e pronto",
                f"mudei tua rota para {media} e tranquei o atalho",
                f"acesso ao {app} suspenso enquanto {media} segura a bronca",
            ],
            reasons=reason_clauses,
            closers=[
                "isso aqui e forca anti-burnout aplicada em tempo real",
                "se continuar, o caos pedagogico so cresce",
                "teimosia nao quebra regra, so alimenta o bloqueio",
                "respira e aceita: hoje o descanso venceu",
                "tu nao perde progresso, tu ganha sanidade",
                "meu trabalho e ser inconveniente antes do colapso",
                "cooperar agora reduz sofrimento acumulado",
                "fim da discussao: pausa primeiro, produtividade depois",
            ],
        )

    if context.event == "RELAX_ESCAPE":
        if tone == "light":
            return _build_combo_message(
                context,
                "escape_light",
                openers=[
                    "Tu saiu do video de descanso",
                    "Troca de aba no meio da pausa",
                    "Tentativa de fuga do relax capturada",
                    "Tu saiu da janela recomendada",
                    "Aba paralela apareceu durante a pausa",
                    "Tu trocou foco bem na hora do descanso",
                    "Desvio de rota no relax detectado",
                    "Alt-tab maroto durante descanso",
                ],
                actions=[
                    f"reabri {media} e te trouxe de volta",
                    f"anulei a fuga e reposicionei {media}",
                    f"retornei teu foco para {media}",
                    f"restaurei {media} na frente",
                    f"reancorei tua tela no {media}",
                    f"substitui a aba paralela por {media}",
                    f"recoloquei {media} como prioridade",
                    f"te puxei de volta ao {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "fica nessa janela por um minuto e pronto",
                    "nao precisa lutar com a pausa",
                    "curte o relax e economiza energia mental",
                    "e so um pit stop, nao uma prisao",
                    "teu retorno ao foco vem logo",
                    "essa etapa fecha teu ciclo sem desgaste",
                    "descanso feito direito vale ouro",
                    "teu sistema agradece constancia agora",
                ],
            )
        if tone == "firm":
            return _build_combo_message(
                context,
                "escape_firm",
                openers=[
                    "Tu repetiu a fuga do descanso",
                    "Tu voltou a trocar de aba no meio da pausa",
                    "Novo desvio do relax detectado",
                    "Tu ta insistindo em sair da janela de descanso",
                    "Rota de fuga reapareceu",
                    "Tu ta tentando driblar o video de novo",
                    "Essa desobediencia ja virou padrao",
                    "Troca de foco fora da pausa, de novo",
                ],
                actions=[
                    f"reforcei {media} e bloqueei a rota paralela",
                    f"mantive {media} no comando da tela",
                    f"te devolvi pro {media} imediatamente",
                    f"reabri {media} e removi distracoes produtivas",
                    f"cancelei o atalho e fixei {media}",
                    f"reinstalei {media} como janela principal",
                    f"neutralizei a troca e mantive {media}",
                    f"retomei o controle com {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "insistir so prolonga tua propria novela",
                    "descanso direito te devolve foco de qualidade",
                    "aceita a pausa e fecha esse ciclo sem sofrimento",
                    "quanto mais dribla, mais firme fica o bloqueio",
                    "teimosia custa energia que tu podia guardar",
                    "hoje a regra e simples: relax primeiro",
                    "fazer pausa nao te atrasa, te salva",
                    "colabora que isso acaba mais rapido",
                ],
            )
        if tone == "hard":
            return _build_combo_message(
                context,
                "escape_hard",
                openers=[
                    "Tu ta tentando escapar do relax em sequencia",
                    "Fuga insistente do video principal",
                    "Tu saiu de novo da janela obrigatoria",
                    "Desvio recorrente em pausa forcada",
                    "Modo fuga ta ativo demais",
                    "Tentativas consecutivas de sair do relax",
                    "Teimosia em alt-tab durante descanso aumentou",
                    "Padrao de fuga do descanso confirmado",
                ],
                actions=[
                    f"te reancorei no {media} sem conversa",
                    f"restaurei {media} e mantive bloqueio total da fuga",
                    f"te trouxe de volta ao {media} no ato",
                    f"deixei {media} fixo e removi teu atalho de escape",
                    f"reassumi a frente com {media}",
                    f"anulei de novo a saida e reposicionei {media}",
                    f"recuperei tua tela pro {media}",
                    f"restitui o {media} como destino unico",
                ],
                reasons=reason_clauses,
                closers=[
                    "ja deu de brincar de fuga, respira e fica ai",
                    "teu cerebro precisa dessa parada mais que teu ego",
                    "insistir nisso e pedir burnout parcelado",
                    "pausa agora, qualidade depois",
                    "descanso incompleto vira foco ruim la na frente",
                    "cooperar te devolve controle mais cedo",
                    "nao sabota teu proprio rendimento de amanha",
                    "relax de verdade e parte da entrega",
                ],
            )
        if tone == "rage":
            return _build_combo_message(
                context,
                "escape_rage",
                openers=[
                    "Tu ta fugindo do descanso na cara dura",
                    "Chega de alt-tab durante pausa obrigatoria",
                    "Fuga do relax em nivel abusado",
                    "Insistencia em escapar passou do limite",
                    "Teimosia no modo descanso virou rotina",
                    "Tentativa de driblar video de novo",
                    "Fuga reincidente, sem surpresa",
                    "Tu insiste em sair justo da janela certa",
                ],
                actions=[
                    f"fixei {media} outra vez e cortei tua manobra",
                    f"trouxe {media} de volta com prioridade maxima",
                    f"reabri {media} e neutralizei tua fuga",
                    f"retomei controle total com {media}",
                    f"restaurei {media} e travei essa escapatoria",
                    f"te empurrei de volta pro {media} no seco",
                    f"desativei teu desvio e mantive {media}",
                    f"resetei tua fuga e reativei {media}",
                ],
                reasons=reason_clauses,
                closers=[
                    "para de negociar com a exaustao",
                    "teimosia so alimenta o modo chato do sistema",
                    "a pausa e pra tua saude mental, nao pra me irritar",
                    "aceita o relax e encerra essa batalha inutil",
                    "eu te bloqueio hoje pra tu nao travar amanha",
                    "descansa direito e evita virar zumbi de teclado",
                    "cooperar e mais inteligente que insistir",
                    "segura esse minuto e a vida segue",
                ],
            )
        return _build_combo_message(
            context,
            "escape_chaos",
            openers=[
                "Escape infinito durante descanso confirmado",
                "Tu entrou no loop de fuga sem freio",
                "Fuga virou modo de vida nesse ciclo",
                "Insistencia caotica em sair do relax",
                "Tu ta duelando com a pausa e perdendo",
                "Fuga teimosa em estado maximo",
                "Desvio compulsivo do descanso no pico",
                "A guerra contra o video de relax chegou no endgame",
            ],
            actions=[
                f"mantive {media} soberano e anulei qualquer escape",
                f"reinstalei {media} como destino absoluto",
                f"prendi teu foco no {media} ate esfriar a correria",
                f"bloqueio total: sem fuga, so {media}",
                f"te puxei de volta pro {media} e fechei a torneira de desvios",
                f"fixei {media} como unica rota disponivel",
                f"neutralizei tua evasao e restabeleci {media}",
                f"reassumi a tela com {media} em modo dominante",
            ],
            reasons=reason_clauses,
            closers=[
                "fim da novela: pausa primeiro, resto depois",
                "quanto mais corre, mais eu travo",
                "descanso venceu essa rodada e ta tudo bem",
                "isso e anticolapso em versao teimosa",
                "tu nao perde tempo, tu recupera sanidade",
                "meu papel e ser inconveniente no momento certo",
                "sossega um minuto e retoma inteiro",
                "manual de sobrevivencia: respirar antes de produzir",
            ],
        )

    return _finalize_local_message("Intervencao anti-burnout acionada: respira e deixa teu cerebro em modo cochilo")


def _openai_alert_message(prompt: str, context: AlertContext) -> str | None:
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
    message = _strip_technical_prefix(message)
    if not message:
        return None
    if _is_low_quality_llm_message(message):
        return None
    if not _is_contextual_llm_message(context, message):
        return None
    return message


def _ollama_alert_message(prompt: str, context: AlertContext) -> str | None:
    if not _ollama_enabled():
        return None

    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "system": _llm_system_instructions(),
        "stream": False,
        "keep_alive": _ollama_keep_alive(),
        "options": {
            "temperature": 0.32,
            "num_predict": _ollama_num_predict(),
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
    message = _strip_technical_prefix(message)
    if not message:
        return None
    if _is_low_quality_llm_message(message):
        return None
    if not _is_contextual_llm_message(context, message):
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


def _set_last_alert_backend(backend: str) -> None:
    global _LAST_ALERT_BACKEND
    with _ALERT_LOCK:
        _LAST_ALERT_BACKEND = (backend or "local").strip().lower()


def get_last_alert_backend() -> str:
    with _ALERT_LOCK:
        return _LAST_ALERT_BACKEND


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
        cached_message, cached_backend = _LLM_CACHE[key]
        _set_last_alert_backend(cached_backend)
        return cached_message

    prompt = _build_alert_prompt(context)

    generated: str | None = None
    used_backend: str | None = None
    for backend in _backend_order():
        if backend == "ollama":
            generated = _ollama_alert_message(prompt, context)
        elif backend == "openai":
            generated = _openai_alert_message(prompt, context)
        else:
            generated = None

        if generated:
            used_backend = backend
            break

    if not generated:
        return None

    normalized_backend = (used_backend or "local").strip().lower()
    _LLM_CACHE[key] = (generated, normalized_backend)
    _set_last_alert_backend(normalized_backend)
    return generated


def build_alert_message(context: AlertContext) -> str:
    llm_message = _llm_alert_message(context)
    if llm_message:
        return llm_message

    _set_last_alert_backend("local")
    return _finalize_local_message(_local_alert_message(context))
