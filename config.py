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
PRE_BLOCK_POPUP_SECONDS = 1.2

# Escalation schedules (seconds)
REST_SCHEDULE = [60, 40, 60, 90, 120, 150, 180, 240]
WORK_SCHEDULE = [60, 50, 45, 40, 35, 30, 25, 20]

# Safety switches
DEV_MODE = os.getenv("AB_DEV_MODE", "1") != "0"
ENABLE_OVERLAY = os.getenv("AB_ENABLE_NOTIFICATIONS", os.getenv("AB_ENABLE_OVERLAY", "1")) != "0"

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

# For now keep only one forced relax window to avoid opening storms.
# Later we can raise this to 2/3 for the "chaos escalation" demo.
RELAX_MAX_SIMULTANEOUS_VIDEOS = 1

# Relax video queries used to resolve URLs dynamically.
RELAX_QUERIES = [
    "relaxing nature scenery 4k",
    "ocean waves relaxing sounds",
    "forest birds ambience no talking",
    "waterfall meditation ambience",
    "rain sounds cozy nature",
]

# Logging
LOG_PATH = os.path.join("logs", "events.jsonl")
