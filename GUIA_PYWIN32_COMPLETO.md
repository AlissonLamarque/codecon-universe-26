# Guia Completo: Anti-Burnout com Python + pywin32 (Windows)

## 1. Objetivo
Construir um app de bandeja (tray icon) no Windows que:
1. Monitora a janela em foco.
2. Detecta apps produtivos.
3. Bloqueia durante descanso forçado.
4. Libera janelas curtas de produtividade.
5. Escala o descanso até o teto (42 min).
6. Permite **Ativar/Pausar/Sair** pelo ícone da bandeja.

Este guia está em ordem de execução, do zero ao `.exe`.

---

## 2. Por que pywin32 (mesmo com docs “feias”)
`pywin32` é um wrapper das APIs nativas do Windows. Para este caso, ele é forte porque:
1. Acesso direto à janela em foco (`GetForegroundWindow`).
2. Acesso ao PID da janela (`GetWindowThreadProcessId`).
3. Controle de mensagens de janela (`PostMessage` com `WM_CLOSE`).
4. Comportamento previsível em Windows 10/11.

Em resumo: a documentação visual pode ser antiga, mas a camada técnica é a certa para controlar janela/processo no Windows.

---

## 3. Escopo do MVP (1 dia)
### Vai ter
1. Monitoramento de app ativo.
2. Lista de apps produtivos.
3. Estado `DESCANSO` vs `PRODUTIVIDADE`.
4. Bloqueio (fecha janela/processo alvo).
5. Abertura de vídeo relaxante.
6. Tray icon com `Ativar/Pausar/Sair`.
7. Logs.

### Não vai ter
1. Persistência automática no boot.
2. Proteção anti-bypass real.
3. Modo serviço Windows (Session 0 atrapalha UI).

---

## 4. Arquitetura (componentes)
1. `monitor.py`: lê janela em foco (`hwnd`, `pid`, nome do processo, título).
2. `policy.py`: decide se o processo é produtivo.
3. `state_machine.py`: controla fases e timers.
4. `enforcer.py`: aplica bloqueio e dispara distração.
5. `tray_app.py`: ícone da bandeja e menu.
6. `main.py`: orquestra tudo.

---

## 5. Pré-requisitos
1. Windows 10/11.
2. Python 3.10+.
3. PowerShell.

### Criar ambiente
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Instalar dependências
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

## 7. Configuração central (`config.py`)
```python
PRODUCTIVE_APPS = {
    "Code.exe",
    "devenv.exe",
    "idea64.exe",
    "cmd.exe",
    "powershell.exe",
    "excel.exe",
}

# Descanso cresce por ciclo até 42 min (em segundos)
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

## 10. Máquina de estados (`state_machine.py`)
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

## 11. Enforcer (bloqueio e distração) (`enforcer.py`)
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
    # Quanto maior o nível, mais caos: abre 1, 2 ou 3 vídeos.
    count = 1 if level < 3 else 2 if level < 6 else 3
    for i in range(count):
        url = VIDEO_URLS[i % len(VIDEO_URLS)]
        subprocess.Popen(["cmd", "/c", "start", url])
```

---

## 12. Ícone de bandeja com menu (`tray_app.py`)
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

## 13. Orquestração principal (`main.py`)
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

## 14. Ordem de execução (resumo operacional)
1. Usuário abre `main.py` (ou `.exe`).
2. App cria thread de monitoramento.
3. App cria tray icon.
4. Estado inicial é `REST_FORCED`.
5. Se abrir app produtivo no descanso, bloqueia.
6. Ao fim do descanso, entra em produtividade temporária.
7. Ao fim da produtividade, volta ao descanso com nível maior.
8. Usuário pausa/ativa/sai pelo tray.

---

## 15. Como rodar em desenvolvimento
```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

### Como encerrar
1. Clique no ícone da bandeja.
2. `Sair`.

---

## 16. Como gerar `.exe` (PyInstaller)
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout main.py
```

Saída padrão:
1. `dist\AntiBurnout.exe`

Observação:
1. Se faltar recurso no build, use `--collect-all pystray`.

---

## 17. Executável vs Serviço (decisão final)
### Use executável
1. Roda na sessão do usuário (tem acesso à UI).
2. Funciona com tray icon e menu clicável.
3. Simples para hackathon.

### Não use serviço no MVP
1. Serviços rodam em Session 0.
2. UI interativa (overlay/vídeo/tray) fica problemática.
3. Complexidade desnecessária para 1 dia.

---

## 18. Checklist de teste manual (rápido)
1. Abrir app, confirmar ícone na bandeja.
2. Em descanso, abrir VS Code e ver bloqueio.
3. Ver vídeo abrir.
4. Esperar transição para produtividade e confirmar liberação.
5. Esperar retorno ao descanso e confirmar escalonamento.
6. Clicar `Ativo` para pausar e confirmar que para de bloquear.
7. Clicar `Sair` e confirmar encerramento.

---

## 19. Problemas comuns e correções
1. **`ModuleNotFoundError: win32gui`**
   - Reinstalar dependências no venv correto: `pip install pywin32`.
2. **Processo não bloqueia**
   - Conferir nome real do processo no log.
3. **Abre vídeo demais**
   - Aumentar `POLL_INTERVAL_SECONDS` e adicionar cooldown por bloqueio.
4. **Sem ícone na bandeja**
   - Verificar `pystray` + `pillow` instalados.
5. **PowerShell mostra acento quebrado**
   - Normal de encoding do terminal; arquivo em UTF-8 pode estar correto.

---

## 20. Hardening mínimo para não “virar vírus” no dev
1. Nunca iniciar com Windows automaticamente.
2. Sempre ter menu `Ativo/Pausar/Sair`.
3. Durante desenvolvimento, manter `Code.exe` fora da lista produtiva quando necessário.
4. Logar todas as ações de bloqueio.
5. Trabalhar em VM se quiser testar modo agressivo.

---

## 21. APIs Win32 usadas (mapa rápido)
1. `win32gui.GetForegroundWindow`: pega `hwnd` ativo.
2. `win32process.GetWindowThreadProcessId`: pega PID da janela.
3. `win32gui.GetWindowText`: pega título da janela.
4. `win32gui.PostMessage(..., WM_CLOSE, ...)`: pede fechamento gracioso.
5. `win32con.WM_CLOSE`: constante da mensagem de fechamento.

---

## 22. Próximo passo direto
Se quiser avançar já com implementação real no repositório:
1. Eu crio os arquivos (`main.py`, `monitor.py`, etc.).
2. Deixo rodando com tray icon funcional.
3. Entrego com comando de build `.exe` validado.


