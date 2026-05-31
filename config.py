import os

# Core behavior
POLL_INTERVAL_SECONDS = 0.30
# Cooldown for normal rest-mode intervention.
# Kept short so repeated productive attempts are blocked again quickly.
BLOCK_COOLDOWN_SECONDS = 0.50
PANIC_COOLDOWN_SECONDS = 1.2
RELAX_ESCAPE_COOLDOWN_SECONDS = 0.8
# Cooldown for opening relax media and sending alert notifications.
# Keeps aggressive minimization without stacking browser tabs/notifications.
MEDIA_COOLDOWN_SECONDS = 5.0
PRE_BLOCK_POPUP_SECONDS = 4.0
# Popup escalation during repeated disobedience:
# starts from PRE_BLOCK_POPUP_SECONDS and grows by steps.
PRE_BLOCK_POPUP_STEP_EVERY_ATTEMPTS = int(os.getenv("AB_PRE_BLOCK_POPUP_STEP_EVERY_ATTEMPTS", "3"))
PRE_BLOCK_POPUP_STEP_SECONDS = float(os.getenv("AB_PRE_BLOCK_POPUP_STEP_SECONDS", "0.8"))
PRE_BLOCK_POPUP_MAX_SECONDS = float(os.getenv("AB_PRE_BLOCK_POPUP_MAX_SECONDS", "8.0"))
# Popup storm escalation (multiple popups / visible insanity)
PRE_BLOCK_POPUP_STORM_FROM_STAGE = int(os.getenv("AB_PRE_BLOCK_POPUP_STORM_FROM_STAGE", "4"))
PRE_BLOCK_POPUP_STORM_MAX_COPIES = int(os.getenv("AB_PRE_BLOCK_POPUP_STORM_MAX_COPIES", "4"))
PRE_BLOCK_POPUP_STORM_STEP_STAGE = int(os.getenv("AB_PRE_BLOCK_POPUP_STORM_STEP_STAGE", "2"))
PRE_BLOCK_POPUP_STORM_STAGGER_SECONDS = float(os.getenv("AB_PRE_BLOCK_POPUP_STORM_STAGGER_SECONDS", "0.12"))
# Persistent side panel (right side) with intervention text.
SIDE_ALERT_ENABLED = os.getenv("AB_SIDE_ALERT_ENABLED", "1") != "0"
SIDE_ALERT_BASE_SECONDS = float(os.getenv("AB_SIDE_ALERT_BASE_SECONDS", "16.0"))
SIDE_ALERT_STAGE_STEP_SECONDS = float(os.getenv("AB_SIDE_ALERT_STAGE_STEP_SECONDS", "2.0"))
SIDE_ALERT_MAX_SECONDS = float(os.getenv("AB_SIDE_ALERT_MAX_SECONDS", "42.0"))
SIDE_ALERT_RIGHT_MARGIN = int(os.getenv("AB_SIDE_ALERT_RIGHT_MARGIN", "22"))
SIDE_ALERT_TOP_RATIO = float(os.getenv("AB_SIDE_ALERT_TOP_RATIO", "0.16"))
SIDE_ALERT_TITLE = os.getenv("AB_SIDE_ALERT_TITLE", "Espirito de Epicuro")
SIDE_ALERT_SUBTITLE = os.getenv("AB_SIDE_ALERT_SUBTITLE", "Ataraxia assistida")

# Rest-time rage extension: when user disobeys during forced rest, add extra
# rest time dynamically. Set AB_REST_EXTENSION_ENABLED=0 to disable.
REST_EXTENSION_ENABLED = os.getenv("AB_REST_EXTENSION_ENABLED", "1") != "0"
# Number of disobediences before starting to add extra rest time.
# This keeps early interventions funny without immediately punishing the timer.
REST_EXTENSION_START_AFTER_ATTEMPTS = int(os.getenv("AB_REST_EXTENSION_START_AFTER_ATTEMPTS", "4"))
REST_EXTENSION_BASE_SECONDS = int(os.getenv("AB_REST_EXTENSION_BASE_SECONDS", "2"))
REST_EXTENSION_PER_ATTEMPT_SECONDS = int(os.getenv("AB_REST_EXTENSION_PER_ATTEMPT_SECONDS", "1"))
REST_EXTENSION_RAGE_EVERY = int(os.getenv("AB_REST_EXTENSION_RAGE_EVERY", "6"))
REST_EXTENSION_RAGE_BONUS_SECONDS = int(os.getenv("AB_REST_EXTENSION_RAGE_BONUS_SECONDS", "2"))
REST_EXTENSION_MAX_PER_EVENT_SECONDS = int(os.getenv("AB_REST_EXTENSION_MAX_PER_EVENT_SECONDS", "18"))
# 0 means unlimited (infinite chaos mode).
REST_EXTENSION_MAX_TOTAL_SECONDS = int(os.getenv("AB_REST_EXTENSION_MAX_TOTAL_SECONDS", "0"))

# Escalation schedules (seconds)
REST_SCHEDULE = [60, 40, 60, 90, 120, 150, 180, 240]
WORK_SCHEDULE = [60, 50, 45, 40, 35, 30, 25, 20]

# Safety switches
DEV_MODE = os.getenv("AB_DEV_MODE", "1") != "0"
ENABLE_OVERLAY = os.getenv("AB_ENABLE_NOTIFICATIONS", os.getenv("AB_ENABLE_OVERLAY", "1")) != "0"

# Windows toast policy:
# - "status": only phase-change toasts + occasional important alerts
# - "all": every alert event (legacy behavior)
NOTIFICATION_MODE = os.getenv("AB_NOTIFICATION_MODE", "status").strip().lower()
# In status mode, intervention toasts appear every N violations (or panic).
IMPORTANT_NOTIFICATION_EVERY_ATTEMPTS = int(os.getenv("AB_IMPORTANT_NOTIFICATION_EVERY_ATTEMPTS", "4"))
# Minimum gap between Windows toasts in status mode.
STATUS_NOTIFICATION_MIN_SECONDS = float(os.getenv("AB_STATUS_NOTIFICATION_MIN_SECONDS", "8.0"))

# Productive process names on Windows
PRODUCTIVE_APPS = {
    "Code.exe",
    "devenv.exe",
    "idea64.exe",
    "pycharm64.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "excel.exe",
    "WINWORD.EXE",
    "msaccess.exe",
    "notepad++.exe",
}

# Never block these (self-protection)
PROTECTED_APPS = {
    "python.exe",
    "pythonw.exe",
    "AntiBurnout.exe",
}

# In dev mode, do not block your coding shell/editor
DEV_MODE_ALLOWLIST = {
    "Code.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "WindowsTerminal.exe",
}

# Panic mode targets: when panic is ON, these apps trigger intervention
# even during productivity window.
PANIC_TARGET_APPS = {
    "Code.exe",
}

RELAX_BROWSER_PROCESSES = {
    "msedge.exe",
    "chrome.exe",
    "brave.exe",
    "firefox.exe",
}

RELAX_TITLE_KEYWORDS = (
    "youtube",
    "anti-burnout",
    "descanso obrig",
    "relax",
)

# Max cap for simultaneous relax windows. Actual count is stage-based.
RELAX_MAX_SIMULTANEOUS_VIDEOS = int(os.getenv("AB_RELAX_MAX_SIMULTANEOUS_VIDEOS", "3"))
RELAX_MULTI_VIDEO_FROM_STAGE_2 = int(os.getenv("AB_RELAX_MULTI_VIDEO_FROM_STAGE_2", "4"))
RELAX_MULTI_VIDEO_FROM_STAGE_3 = int(os.getenv("AB_RELAX_MULTI_VIDEO_FROM_STAGE_3", "6"))

# Legacy pool (fallback).
RELAX_QUERIES = [
    "relaxing nature scenery 4k",
    "ocean waves relaxing sounds",
    "forest birds ambience no talking",
    "waterfall meditation ambience",
    "rain sounds cozy nature",
]

# Stage-based pools used by madness escalation.
# As the user keeps disobeying during forced rest, the app moves from calm
# nature media into progressively absurd content.
RELAX_QUERY_TIERS = [
    [
        "relaxing nature scenery 4k",
        "ocean waves relaxing sounds",
        "forest birds ambience no talking",
        "waterfall meditation ambience",
        "rain sounds cozy nature",
    ],
    [
        "cozy fireplace ambience 4k no talking",
        "lofi chill beats no lyrics calm",
        "soft ambient rain for stress relief",
        "healing nature ambience cinematic",
    ],
    [
        "slime asmr satisfying no talking",
        "oddly satisfying compilation no talking",
        "kinetic sand cutting satisfying",
        "soap cutting satisfying asmr visual",
        "calming slime satisfying video",
    ],
    [
        "spinning fish loop 1 hour",
        "rotating fish meme loop clean",
        "dvd logo bouncing corner loop",
        "windows pipes screensaver loop",
        "endless tunnel optical illusion loop",
    ],
    [
        "trippy fish spinning low quality loop",
        "brainrot fish loop clean",
        "how to fix a cat",
        "how to fix a cat low quality meme",
        "spinning rat low quality",
        "rat spinning meme loop",
        "spinning pickup truck",
        "pickup truck spinning low poly loop",
        "slime asmr brainrot edit clean",
        "npc ahh low quality loop",
        "xiao ling theme song low quality loop",
        "subway surfers theme song very low quality",
        "funk do tralalero tralala",
        "tralalero tralala low quality meme",
        "kakashi naruto can be hard sometimes clip",
        "kakashi falando naruto pode ser duro as vezes",
        "naruto can be hard sometimes meme",
        "kurapika esta se afundando em um vazio indescritivel",
        "kurapika afundando em um vazio indescritivel clip",
        "kurapika drowning in an indescribable emptiness meme",
        "gojo phonk low quality edit loop",
        "gigachad sigma low quality brainrot loop",
        "skibidi toilet low quality loop clean",
        "brazilian corecore meme low quality",
        "deep fried anime meme compilation clean",
        "yamete kudasai low quality meme loop",
        "compressed weirdcore loop no jumpscare",
        "ps1 style surreal loop video",
        "chaotic low quality loop for dopamine",
        "endless loading screen corecore loop",
    ],
]

# Logging
LOG_PATH = os.path.join("logs", "events.jsonl")
