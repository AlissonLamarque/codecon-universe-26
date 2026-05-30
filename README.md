# Anti-Burnout (Hackathon MVP)

Satirical anti-productivity app for Windows with inverted pomodoro, tray controls, panic mode, and forced relax videos.

## Quick install (2 minutes)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run
```powershell
python main.py
```

Default behavior now opens a **launcher window** where you choose startup mode:
1. `Dev safe` (does not block VSCode/terminal)
2. `Live normal`
3. `Panic demo` (aggressive VSCode intervention)

If you build the executable, double-clicking `dist\\AntiBurnout.exe` also opens this launcher first.

## Tray controls (runtime)
1. `Ativo` -> enable/disable all interventions (blocking, notifications, and relax media).
2. `Modo dev` -> safe mode for development.
3. `Modo panico` -> force intervention on VSCode focus.
4. `Notificacoes` -> toggle Windows notifications without restart.
5. `Sair` -> exit app.

## Alert agent
By default, the app uses a local contextual alert agent. It can optionally call an LLM to generate more specific Windows notifications for the productive app and relax media.

During a forced rest, repeated attempts to return to productive apps escalate the agent tone into a more autocratic "rest authority" mode.

Enable LLM alerts:
```powershell
$env:OPENAI_API_KEY="your_api_key"
$env:AB_ENABLE_LLM_ALERTS="1"
# Optional:
$env:AB_ALERT_MODEL="gpt-5.2"
$env:AB_ALERT_TIMEOUT_SECONDS="2.5"
python main.py
```

If the LLM call fails, times out, or is disabled, the local alert agent is used automatically.

## Optional CLI startup flags
```powershell
python main.py --no-launcher --profile dev
python main.py --no-launcher --profile live
python main.py --no-launcher --profile panic
python main.py --no-launcher --live --no-notifications
```

## Build .exe
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout main.py
```

Output:
`dist\\AntiBurnout.exe`
