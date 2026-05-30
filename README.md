# Anti-Burnout (Hackathon MVP)

App satirico "anti produtividade" para Windows, com pomodoro invertido, bloqueio de apps produtivos em descanso e escalonamento de caos.

## Como rodar
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Modos
1. `python main.py` -> modo dev (padrao, nao bloqueia VS Code/terminal).
2. `python main.py --live` -> modo demo agressivo (bloqueia apps da lista produtiva).
3. `python main.py --no-overlay` -> sem overlay piscante.

## Tray icon
1. `Ativo` (check) -> liga/desliga bloqueio.
2. `Modo dev` -> quando ON, nao bloqueia VS Code/terminal.
3. `Modo panico` -> quando ON, focar no VS Code dispara bloqueio + video mesmo fora do descanso.
4. `Sair` -> encerra o processo.

## Build para .exe
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout main.py
```

Saida:
`dist\\AntiBurnout.exe`
