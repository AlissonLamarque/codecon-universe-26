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
1. `Ativo` -> enable/disable blocking.
2. `Modo dev` -> safe mode for development.
3. `Modo panico` -> force intervention on VSCode focus.
4. `No overlay` -> toggle flashing overlay without restart.
5. `Sair` -> exit app.

## Optional CLI startup flags
```powershell
python main.py --no-launcher --profile dev
python main.py --no-launcher --profile live
python main.py --no-launcher --profile panic
python main.py --no-launcher --live --no-overlay
```

## Build .exe
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout main.py
```

Output:
`dist\\AntiBurnout.exe`
