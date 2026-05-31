"""
meme_messages.py — Mensagens meme dinâmicas para o overlay de descanso.

Módulo responsável por fornecer frases cômicas que são exibidas
no overlay fullscreen durante o período de descanso compulsório.
Usa seleção aleatória com anti-repetição para manter o fator surpresa.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Banco de frases cômicas do Método Comodoro™
# ---------------------------------------------------------------------------
MEME_MESSAGES: list[str] = [
    # Frases solicitadas pelo usuário
    "Produtividade detectada. Isso é perigoso para sua paz interior.",
    "Seu cérebro pediu férias e você abriu o VSCode.",
    "Descanso compulsório ativado pelo Ministério da Dopamina.",

    # Frases extras na mesma pegada
    "O burnout ligou. Disse que está a caminho. Relaxe antes que ele chegue.",
    "Você foi flagrado tentando ser útil. Isso é uma infração grave.",
    "Alerta: níveis de responsabilidade acima do permitido por lei.",
    "Seu commit pode esperar. Sua sanidade, não.",
    "A OMS recomenda: feche a IDE e abra um suco.",
    "URGENTE: Suas costas estão processando você por negligência.",
    "Ctrl+S no seu bem-estar. O código compila depois.",
    "Descansar não é opcional. É deploy em produção da sua saúde.",
    "Seu backlog de sono está maior que o do Jira.",
    "Sprint review do seu corpo: 'preciso de férias, não de mais tasks'.",
    "Você não é uma máquina. Máquinas pelo menos reiniciam.",
    "Tentativa de produtividade interceptada. Redirecionando para o ócio.",
    "Se trabalho fosse bom, os ricos não delegavam.",
    "A cada commit forçado, um neurônio pede demissão.",
    "Modo sofá ativado. Resistência é fútil.",
]

# Guarda o índice da última mensagem exibida para evitar repetição imediata.
_last_index: int | None = None


def get_random_meme() -> str:
    """
    Retorna uma frase meme aleatória, garantindo que não repita
    a última mensagem exibida consecutivamente.
    """
    global _last_index

    if len(MEME_MESSAGES) <= 1:
        return MEME_MESSAGES[0] if MEME_MESSAGES else ""

    while True:
        idx = random.randrange(len(MEME_MESSAGES))
        if idx != _last_index:
            _last_index = idx
            return MEME_MESSAGES[idx]


def get_meme_for_app(app_name: str | None = None) -> str:
    """
    Retorna uma mensagem meme, opcionalmente personalizada
    com o nome do app produtivo que foi detectado.
    Se app_name for fornecido, há 40% de chance de gerar uma
    mensagem contextual em vez de usar o banco genérico.
    """
    app = (app_name or "").strip()

    # Mensagens contextuais por app (usadas com probabilidade de 40%)
    if app and random.random() < 0.4:
        app_memes: dict[str, list[str]] = {
            "Code.exe": [
                f"Você abriu o VS Code. Seu terapeuta foi notificado.",
                f"VS Code detectado. Ativando protocolo anti-código.",
                f"Extensions do VS Code não substituem extensões de vida.",
            ],
            "devenv.exe": [
                f"Visual Studio? Neste horário? Isso é um cry for help.",
                f"Feche o Visual Studio. Abra a Visual Paz Interior.",
            ],
            "excel.exe": [
                f"Planilha detectada. Sua vida não é uma célula do Excel.",
                f"PROCV no seu bem-estar retornou #N/D. Descanse.",
            ],
            "WINWORD.EXE": [
                f"Word aberto? Escreva 'eu mereço descanso' 100 vezes.",
            ],
            "idea64.exe": [
                f"IntelliJ detectado. Até a JVM precisa de garbage collection. Você também.",
            ],
            "pycharm64.exe": [
                f"PyCharm? Mais como Py-Calma. Hora de parar.",
            ],
        }
        contextual = app_memes.get(app)
        if contextual:
            return random.choice(contextual)

    return get_random_meme()
