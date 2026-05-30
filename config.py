import os

# Core behavior
POLL_INTERVAL_SECONDS = 0.30
# Cooldown for normal rest-mode intervention.
# Kept short so repeated productive attempts are blocked again quickly.
BLOCK_COOLDOWN_SECONDS = 0.50
PANIC_COOLDOWN_SECONDS = 1.2

# Escalation schedules (seconds)
REST_SCHEDULE = [60, 180, 300, 480, 780, 1260, 2040, 2520]  # max 42 min
WORK_SCHEDULE = [360, 360, 300, 300, 240, 180, 120, 120]

# Safety switches
DEV_MODE = os.getenv("AB_DEV_MODE", "1") != "0"
ENABLE_OVERLAY = os.getenv("AB_ENABLE_OVERLAY", "1") != "0"
OVERLAY_SECONDS = 4

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
