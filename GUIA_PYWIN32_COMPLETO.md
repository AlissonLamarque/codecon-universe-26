# Guia Completo: Anti-Burnout com Python + pywin32 (Windows)

## 1. Objetivo
Construir um app de bandeja (tray icon) no Windows que:
1. Monitora a janela em foco.
2. Detecta apps produtivos.
3. Bloqueia durante descanso forÃ§ado.
4. Libera janelas curtas de produtividade.
5. Escala o descanso atÃ© o teto (42 min).
6. Permite **Ativar/Pausar/Sair** pelo Ã­cone da bandeja.

Este guia estÃ¡ em ordem de execuÃ§Ã£o, do zero ao `.exe`.

---

## 2. Por que pywin32 (mesmo com docs â€œfeiasâ€)
`pywin32` Ã© um wrapper das APIs nativas do Windows. Para este caso, ele Ã© forte porque:
1. Acesso direto Ã  janela em foco (`GetForegroundWindow`).
2. Acesso ao PID da janela (`GetWindowThreadProcessId`).
3. Controle de mensagens de janela (`PostMessage` com `WM_CLOSE`).
4. Comportamento previsÃ­vel em Windows 10/11.

Em resumo: a documentaÃ§Ã£o visual pode ser antiga, mas a camada tÃ©cnica Ã© a certa para controlar janela/processo no Windows.

---

## 3. Escopo do MVP (1 dia)
### Vai ter
1. Monitoramento de app ativo.
2. Lista de apps produtivos.
3. Estado `DESCANSO` vs `PRODUTIVIDADE`.
4. Bloqueio (fecha janela/processo alvo).
5. Abertura de vÃ­deo relaxante.
6. Tray icon com `Ativar/Pausar/Sair`.
7. Logs.

### NÃ£o vai ter
1. PersistÃªncia automÃ¡tica no boot.
2. ProteÃ§Ã£o anti-bypass real.
3. Modo serviÃ§o Windows (Session 0 atrapalha UI).

---

## 4. Arquitetura (componentes)
1. `monitor.py`: lÃª janela em foco (`hwnd`, `pid`, nome do processo, tÃ­tulo).
2. `policy.py`: decide se o processo Ã© produtivo.
3. `state_machine.py`: controla fases e timers.
4. `enforcer.py`: aplica bloqueio e dispara distraÃ§Ã£o.
5. `tray_app.py`: Ã­cone da bandeja e menu.
6. `main.py`: orquestra tudo.

---

## 5. PrÃ©-requisitos
1. Windows 10/11.
2. Python 3.10+.
3. PowerShell.

### Criar ambiente
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Instalar dependÃªncias
```powershell
pip install pywin32 psutil pystray pillow
```

---

## 6. Estrutura de pastas recomendada
```text
anti-burnout/
  main.py
  monitor.py
  policy.py
  state_machine.py
  enforcer.py
  tray_app.py
  config.py
  logs/
    events.jsonl
```

---

## 7. ConfiguraÃ§Ã£o central (`config.py`)
```python
PRODUCTIVE_APPS = {
    "Code.exe",
    "devenv.exe",
    "idea64.exe",
    "cmd.exe",
    "powershell.exe",
    "excel.exe",
}

# Descanso cresce por ciclo atÃ© 42 min (em segundos)
REST_SCHEDULE = [60, 180, 300, 480, 780, 1260, 2040, 2520]

# Produtividade encolhe no tempo (em segundos)
WORK_SCHEDULE = [360, 360, 300, 300, 240, 180, 120, 120]

VIDEO_URLS = [
    "https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k",
    "https://www.youtube.com/results?search_query=ocean+waves+relaxing+sounds",
    "https://www.youtube.com/results?search_query=forest+birds+ambience+no+talking",
]

POLL_INTERVAL_SECONDS = 0.30
LOG_PATH = "logs/events.jsonl"
```

---

## 8. Monitor de janela ativa (`monitor.py`)
```python
import win32gui
import win32process
import psutil

def get_active_window_info():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None

    title = win32gui.GetWindowText(hwnd) or ""
    _, pid = win32process.GetWindowThreadProcessId(hwnd)

    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except Exception:
        return None

    return {
        "hwnd": hwnd,
        "pid": pid,
        "process_name": name,
        "title": title,
    }
```

---

## 9. Regra de produtividade (`policy.py`)
```python
from config import PRODUCTIVE_APPS

def is_productive(process_name: str | None) -> bool:
    if not process_name:
        return False
    return process_name in PRODUCTIVE_APPS
```

---

## 10. MÃ¡quina de estados (`state_machine.py`)
```python
import time
from dataclasses import dataclass
from config import REST_SCHEDULE, WORK_SCHEDULE

REST_FORCED = "REST_FORCED"
PRODUCTIVE_WINDOW = "PRODUCTIVE_WINDOW"

@dataclass
class CycleState:
    phase: str = REST_FORCED
    cycle_index: int = 0
    phase_started_at: float = 0.0

    def start(self):
        self.phase_started_at = time.time()

    def current_rest_seconds(self) -> int:
        idx = min(self.cycle_index, len(REST_SCHEDULE) - 1)
        return REST_SCHEDULE[idx]

    def current_work_seconds(self) -> int:
        idx = min(self.cycle_index, len(WORK_SCHEDULE) - 1)
        return WORK_SCHEDULE[idx]

    def phase_elapsed(self) -> float:
        return time.time() - self.phase_started_at

    def update(self):
        if self.phase == REST_FORCED and self.phase_elapsed() >= self.current_rest_seconds():
            self.phase = PRODUCTIVE_WINDOW
            self.phase_started_at = time.time()
            return "ENTER_WORK"

        if self.phase == PRODUCTIVE_WINDOW and self.phase_elapsed() >= self.current_work_seconds():
            self.phase = REST_FORCED
            self.phase_started_at = time.time()
            self.cycle_index += 1
            return "ENTER_REST"

        return None
```

---

## 11. Enforcer (bloqueio e distraÃ§Ã£o) (`enforcer.py`)
```python
import subprocess
import time
import psutil
import win32gui
import win32con
from config import VIDEO_URLS

def close_window_gracefully(hwnd: int):
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False

def kill_process(pid: int):
    try:
        p = psutil.Process(pid)
        p.terminate()
        try:
            p.wait(timeout=1.0)
        except Exception:
            p.kill()
        return True
    except Exception:
        return False

def block_productive_window(hwnd: int, pid: int):
    # 1) tenta fechar educadamente
    close_window_gracefully(hwnd)
    time.sleep(0.2)
    # 2) fallback: mata processo
    kill_process(pid)

def open_relax_video(level: int):
    # Quanto maior o nÃ­vel, mais caos: abre 1, 2 ou 3 vÃ­deos.
    count = 1 if level < 3 else 2 if level < 6 else 3
    for i in range(count):
        url = VIDEO_URLS[i % len(VIDEO_URLS)]
        subprocess.Popen(["cmd", "/c", "start", url])
```

---

## 12. Ãcone de bandeja com menu (`tray_app.py`)
```python
from dataclasses import dataclass
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

@dataclass
class UiState:
    enabled: bool = True
    running: bool = True

def create_icon_image():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="red")
    d.text((20, 20), "Zz", fill="white")
    return img

def build_tray(ui_state: UiState):
    def on_toggle(icon, item):
        ui_state.enabled = not ui_state.enabled
        icon.update_menu()

    def on_quit(icon, item):
        ui_state.running = False
        icon.stop()

    menu = Menu(
        MenuItem("Ativo", on_toggle, checked=lambda item: ui_state.enabled),
        MenuItem("Sair", on_quit),
    )
    return Icon("anti_burnout", create_icon_image(), "Anti-Burnout", menu)
```

---

## 13. OrquestraÃ§Ã£o principal (`main.py`)
```python
import json
import os
import threading
import time

from config import POLL_INTERVAL_SECONDS, LOG_PATH
from monitor import get_active_window_info
from policy import is_productive
from state_machine import CycleState, REST_FORCED
from enforcer import block_productive_window, open_relax_video
from tray_app import UiState, build_tray

def log_event(payload: dict):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

def monitor_loop(ui_state: UiState):
    cycle = CycleState()
    cycle.start()
    log_event({"event": "APP_STARTED", "phase": cycle.phase, "cycle": cycle.cycle_index})
    open_relax_video(level=cycle.cycle_index)

    while ui_state.running:
        transition = cycle.update()
        if transition == "ENTER_WORK":
            log_event({"event": "ENTER_WORK", "cycle": cycle.cycle_index})
        elif transition == "ENTER_REST":
            log_event({"event": "ENTER_REST", "cycle": cycle.cycle_index})
            open_relax_video(level=cycle.cycle_index)

        if ui_state.enabled and cycle.phase == REST_FORCED:
            info = get_active_window_info()
            if info and is_productive(info["process_name"]):
                block_productive_window(info["hwnd"], info["pid"])
                log_event({
                    "event": "BLOCKED",
                    "process": info["process_name"],
                    "title": info["title"],
                    "cycle": cycle.cycle_index,
                })

        time.sleep(POLL_INTERVAL_SECONDS)

def main():
    ui_state = UiState(enabled=True, running=True)
    t = threading.Thread(target=monitor_loop, args=(ui_state,), daemon=True)
    t.start()

    tray = build_tray(ui_state)
    tray.run()

if __name__ == "__main__":
    main()
```

---

## 14. Ordem de execuÃ§Ã£o (resumo operacional)
1. UsuÃ¡rio abre `main.py` (ou `.exe`).
2. App cria thread de monitoramento.
3. App cria tray icon.
4. Estado inicial Ã© `REST_FORCED`.
5. Se abrir app produtivo no descanso, bloqueia.
6. Ao fim do descanso, entra em produtividade temporÃ¡ria.
7. Ao fim da produtividade, volta ao descanso com nÃ­vel maior.
8. UsuÃ¡rio pausa/ativa/sai pelo tray.

---

## 15. Como rodar em desenvolvimento
```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

### Como encerrar
1. Clique no Ã­cone da bandeja.
2. `Sair`.

---

## 16. Como gerar `.exe` (PyInstaller)
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout main.py
```

SaÃ­da padrÃ£o:
1. `dist\AntiBurnout.exe`

ObservaÃ§Ã£o:
1. Se faltar recurso no build, use `--collect-all pystray`.

---

## 17. ExecutÃ¡vel vs ServiÃ§o (decisÃ£o final)
### Use executÃ¡vel
1. Roda na sessÃ£o do usuÃ¡rio (tem acesso Ã  UI).
2. Funciona com tray icon e menu clicÃ¡vel.
3. Simples para hackathon.

### NÃ£o use serviÃ§o no MVP
1. ServiÃ§os rodam em Session 0.
2. UI interativa (overlay/vÃ­deo/tray) fica problemÃ¡tica.
3. Complexidade desnecessÃ¡ria para 1 dia.

---

## 18. Checklist de teste manual (rÃ¡pido)
1. Abrir app, confirmar Ã­cone na bandeja.
2. Em descanso, abrir VS Code e ver bloqueio.
3. Ver vÃ­deo abrir.
4. Esperar transiÃ§Ã£o para produtividade e confirmar liberaÃ§Ã£o.
5. Esperar retorno ao descanso e confirmar escalonamento.
6. Clicar `Ativo` para pausar e confirmar que para de bloquear.
7. Clicar `Sair` e confirmar encerramento.

---

## 19. Problemas comuns e correÃ§Ãµes
1. **`ModuleNotFoundError: win32gui`**
   - Reinstalar dependÃªncias no venv correto: `pip install pywin32`.
2. **Processo nÃ£o bloqueia**
   - Conferir nome real do processo no log.
3. **Abre vÃ­deo demais**
   - Aumentar `POLL_INTERVAL_SECONDS` e adicionar cooldown por bloqueio.
4. **Sem Ã­cone na bandeja**
   - Verificar `pystray` + `pillow` instalados.
5. **PowerShell mostra acento quebrado**
   - Normal de encoding do terminal; arquivo em UTF-8 pode estar correto.

---

## 20. Hardening mÃ­nimo para nÃ£o â€œvirar vÃ­rusâ€ no dev
1. Nunca iniciar com Windows automaticamente.
2. Sempre ter menu `Ativo/Pausar/Sair`.
3. Durante desenvolvimento, manter `Code.exe` fora da lista produtiva quando necessÃ¡rio.
4. Logar todas as aÃ§Ãµes de bloqueio.
5. Trabalhar em VM se quiser testar modo agressivo.

---

## 21. APIs Win32 usadas (mapa rÃ¡pido)
1. `win32gui.GetForegroundWindow`: pega `hwnd` ativo.
2. `win32process.GetWindowThreadProcessId`: pega PID da janela.
3. `win32gui.GetWindowText`: pega tÃ­tulo da janela.
4. `win32gui.PostMessage(..., WM_CLOSE, ...)`: pede fechamento gracioso.
5. `win32con.WM_CLOSE`: constante da mensagem de fechamento.

---

## 22. PrÃ³ximo passo direto
Se quiser avanÃ§ar jÃ¡ com implementaÃ§Ã£o real no repositÃ³rio:
1. Eu crio os arquivos (`main.py`, `monitor.py`, etc.).
2. Deixo rodando com tray icon funcional.
3. Entrego com comando de build `.exe` validado.


