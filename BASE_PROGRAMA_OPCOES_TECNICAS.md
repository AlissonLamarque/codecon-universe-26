# Base do Programa Anti-Burnout: OpÃ§Ãµes TÃ©cnicas e RecomendaÃ§Ã£o

## Objetivo deste documento
Este documento compara formas reais de implementar a base do programa anti-burnout (monitorar atividade, bloquear apps produtivos, forÃ§ar descanso e escalar o caos), com foco em **entregar algo filmÃ¡vel em 1 dia**.

## O que a base precisa fazer
1. Monitorar o que o usuÃ¡rio abre e usa (processo/janela em foco).
2. Detectar tentativa de uso de app produtivo (`Code.exe`, `idea64.exe`, `excel.exe`, `cmd.exe`, etc.).
3. Interromper/bloquear a tentativa.
4. ForÃ§ar descanso (overlay, alerta piscando, vÃ­deos relaxantes).
5. Liberar uma janela curta de produtividade.
6. Repetir ciclos com escalonamento atÃ© o modo absurdo (descanso crescendo atÃ© 42 min + intervenÃ§Ãµes mais apelativas).

## Arquitetura base (independente da stack)
### Componentes
1. `Monitor`: observa processo/janela ativa.
2. `Policy Engine`: decide se o app Ã© produtivo ou neutro.
3. `State Machine`: alterna entre `REST_FORCED` e `PRODUCTIVE_WINDOW`.
4. `Enforcer`: aplica bloqueio (kill/minimize/overlay/topmost).
5. `Distraction Orchestrator`: abre vÃ­deos, sons, alertas e janelas.
6. `Escalation`: aumenta tempo e intensidade por ciclo.
7. `Logger`: grava eventos para demo e debug.

### Como o fluxo funciona
1. UsuÃ¡rio abre app produtivo.
2. Motor detecta evento em milissegundos/segundos.
3. Se o estado atual for descanso, bloqueia e dispara ritual de descanso.
4. Quando o descanso termina, libera produtividade por `N` minutos.
5. Ao vencer `N`, volta para descanso obrigatÃ³rio com nÃ­vel maior.

---

## OpÃ§Ãµes tÃ©cnicas

## OpÃ§Ã£o A (recomendada): Python + pywin32 + psutil + overlay simples
### Como funciona
1. `pywin32` chama APIs Win32 para janela em foco.
2. `psutil` ajuda a identificar processos, PIDs e metadados.
3. Polling curto (ex.: 200-500 ms) verifica app em foco e estado.
4. `taskkill`/`TerminateProcess` fecha app bloqueado ou minimiza.
5. Overlay topmost (Tkinter/PySide) mostra alerta e bloqueio visual.
6. `subprocess` abre vÃ­deos no player/navegador.

### Exemplo prÃ¡tico mÃ­nimo
```python
import time, subprocess, psutil, win32gui, win32process

PRODUTIVOS = {"Code.exe", "cmd.exe", "excel.exe"}
DESCANSO_ATIVO = True

def processo_em_foco():
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        return psutil.Process(pid).name()
    except Exception:
        return None

while True:
    nome = processo_em_foco()
    if DESCANSO_ATIVO and nome in PRODUTIVOS:
        subprocess.run(["taskkill", "/F", "/IM", nome], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(["cmd", "/c", "start", "https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k"])
    time.sleep(0.3)
```

### Por que usar
1. Entrega rÃ¡pida para hackathon.
2. Muito cÃ³digo pronto e curva de aprendizado baixa.
3. FÃ¡cil iterar regras absurdas sem recompilar toolchain pesada.
4. Boa para demo em vÃ­deo.

### Pontos fracos
1. NÃ£o Ã© blindado contra usuÃ¡rio avanÃ§ado.
2. Controle de foco no Windows tem limitaÃ§Ãµes (algumas mudanÃ§as de foco nÃ£o obedecem sempre).
3. Pode exigir ajustes por versÃ£o/configuraÃ§Ã£o do Windows.

### Quando escolher
Escolha esta opÃ§Ã£o se a meta for **MVP completo em 1 dia**.

---

## OpÃ§Ã£o B: C#/.NET (WPF/WinUI) + APIs Win32/WMI
### Como funciona
1. `ManagementEventWatcher` pode monitorar inÃ­cio de processo (WMI).
2. P/Invoke para APIs Win32 de janela/foco.
3. WPF cria overlay bonito/topmost facilmente.
4. Timers e state machine ficam em um serviÃ§o/app desktop robusto.

### Exemplo prÃ¡tico mÃ­nimo
```csharp
using System.Management;

var watcher = new ManagementEventWatcher(
    "SELECT * FROM Win32_ProcessStartTrace");

watcher.EventArrived += (s, e) =>
{
    var nome = e.NewEvent.Properties["ProcessName"]?.Value?.ToString();
    if (nome == "Code.exe")
    {
        // Exemplo: matar processo e abrir vÃ­deo de descanso
        System.Diagnostics.Process.Start("taskkill", "/F /IM Code.exe");
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo {
            FileName = "https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k",
            UseShellExecute = true
        });
    }
};

watcher.Start();
Console.ReadLine();
```

### Por que usar
1. IntegraÃ§Ã£o nativa forte com Windows.
2. Overlay/UI com acabamento superior.
3. Melhor estrutura para evoluir para produto real depois.

### Pontos fracos
1. Mais tempo de engenharia inicial.
2. Risco de perder tempo com detalhes de UI/build/publicaÃ§Ã£o.
3. Para 1 dia, pode custar mais do que Python.

### Quando escolher
Se o time jÃ¡ domina C# e quer priorizar polish de desktop.

---

## OpÃ§Ã£o C: Electron/Node.js (desktop web)
### Como funciona
1. Processo principal monitora eventos e controla janelas da prÃ³pria app.
2. Bibliotecas de terceiros tentam ler janela ativa/processos.
3. Bloqueio e overlays sÃ£o feitos com `BrowserWindow` topmost.

### Exemplo prÃ¡tico mÃ­nimo
```js
// npm i active-win
const { app, BrowserWindow } = require("electron");
const activeWin = require("active-win");

setInterval(async () => {
  const w = await activeWin();
  const exe = w?.owner?.name; // ex.: Code.exe
  if (exe === "Code.exe") {
    const overlay = new BrowserWindow({ alwaysOnTop: true, fullscreen: true });
    overlay.loadURL("https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k");
  }
}, 400);
```

### Por que usar
1. Time de frontend entrega interface divertida muito rÃ¡pido.
2. Demo visual costuma ficar forte.

### Pontos fracos
1. Controle global de outras apps Ã© menos direto que Win32 puro.
2. DependÃªncia de libs externas pode gerar fricÃ§Ã£o.
3. Peso maior e mais variaÃ§Ã£o de comportamento.

### Quando escolher
Se a demo depende muito de UI teatral e o controle agressivo pode ser "fakeado" no vÃ­deo.

---

## OpÃ§Ã£o D: AutoHotkey + scripts auxiliares
### Como funciona
1. Hooks de hotkey/janela por script.
2. Regras de bloqueio e automaÃ§Ã£o de janelas muito rÃ¡pidas de testar.
3. Pode chamar PowerShell/Python para partes mais complexas.

### Exemplo prÃ¡tico mÃ­nimo
```ahk
#Persistent
SetTimer, WatchApps, 300
return

WatchApps:
WinGet, procName, ProcessName, A
if (procName = "Code.exe") {
    Process, Close, Code.exe
    Run, https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k
}
return
```

### Por que usar
1. ProtÃ³tipo extremamente rÃ¡pido no Windows.
2. Muito bom para automaÃ§Ã£o agressiva visÃ­vel em demo.

### Pontos fracos
1. Manutenibilidade cai rÃ¡pido com lÃ³gica complexa.
2. EscalaÃ§Ã£o de features fica bagunÃ§ada.
3. NÃ£o passa tanto "arquitetura limpa" para avaliaÃ§Ã£o de cÃ³digo.

### Quando escolher
Como plano B ultra-rÃ¡pido, ou combinado com Python.

---

## OpÃ§Ã£o E: Linux X11 (Python + xdotool/wmctrl)
### Como funciona
1. `xdotool`/`wmctrl` manipulam foco e janelas no X11.
2. Scripts monitoram processo e aplicam bloqueios.
3. Overlay pode ser feito com Tkinter/PyQt.

### Exemplo prÃ¡tico mÃ­nimo
```bash
#!/usr/bin/env bash
while true; do
  pid=$(xdotool getactivewindow getwindowpid 2>/dev/null)
  cmd=$(ps -p "$pid" -o comm= 2>/dev/null)
  if [[ "$cmd" == "code" ]]; then
    kill -9 "$pid"
    xdg-open "https://www.youtube.com/results?search_query=relaxing+nature+scenery+4k" >/dev/null 2>&1
  fi
  sleep 0.4
done
```

### Por que usar
1. AutomaÃ§Ã£o global em X11 costuma ser permissiva.
2. Bom para efeitos "caÃ³ticos".

### Pontos fracos
1. Depende de sessÃ£o X11 (nÃ£o Wayland).
2. Comportamento muda por window manager/distribuiÃ§Ã£o.
3. Ambiente da demo precisa estar travado e previsÃ­vel.

### Quando escolher
Se vocÃªs controlam 100% o ambiente Linux e confirmam X11.

---

## OpÃ§Ã£o F: Linux Wayland (nÃ£o recomendado para 1 dia)
### Como funciona
1. Wayland isola apps por design.
2. Controle global de outras janelas/processos Ã© limitado sem caminhos especiais/portais/compositor-specific.

### Exemplo prÃ¡tico mÃ­nimo
```bash
# Em Wayland, o caminho tÃ­pico passa por portais e consentimento do usuÃ¡rio.
# Isso jÃ¡ mostra por que Ã© ruim para hackathon de 1 dia:
systemctl --user status xdg-desktop-portal.service
```

### Por que evitar agora
1. Grande risco tÃ©cnico para prazo curto.
2. O comportamento varia bastante entre compositores.
3. Pode matar o hackathon por problemas de permissÃ£o/integraÃ§Ã£o.

### Quando faria sentido
Projeto de pesquisa maior, sem prazo de 24h.

---

## Comparativo rÃ¡pido (foco: 1 dia)
| OpÃ§Ã£o | Velocidade de entrega | Controle agressivo real | Risco tÃ©cnico | Qualidade de demo |
|---|---|---|---|---|
| Python + pywin32 | Alta | Alta | MÃ©dio | Alta |
| C#/.NET | MÃ©dia | Alta | MÃ©dio | Alta |
| Electron | MÃ©dia | MÃ©dia | MÃ©dio/Alto | Alta |
| AutoHotkey | Muito alta | MÃ©dia/Alta | MÃ©dio | MÃ©dia/Alta |
| Linux X11 | MÃ©dia | Alta | MÃ©dio | Alta |
| Linux Wayland | Baixa | Baixa/MÃ©dia | Alto | Incerta |

---

## ExecutÃ¡vel no Windows ou script como serviÃ§o?
## RecomendaÃ§Ã£o para o hackathon
1. Construam como **script Python rodando na sessÃ£o do usuÃ¡rio**.
2. No final, empacotem em **`.exe` com PyInstaller** (`--onefile --windowed`).
3. Se quiser iniciar automaticamente, usem **Task Scheduler no logon** ou pasta `Startup`.

### Por que nÃ£o usar serviÃ§o Windows no MVP
1. ServiÃ§o roda em Session 0 e nÃ£o Ã© bom para UI interativa (overlay, popups, vÃ­deos).
2. VocÃªs teriam que fazer 2 processos (serviÃ§o + agente de UI), o que aumenta muito o escopo em 1 dia.

### Comandos prÃ¡ticos
```powershell
# Instalar dependÃªncias
pip install pywin32 psutil

# Rodar MVP
python main.py

# Empacotar .exe
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

---

## RecomendaÃ§Ã£o final para vocÃªs
## Escolha: Python + pywin32 no Windows, rodando na sessÃ£o do usuÃ¡rio e empacotado como `.exe`
### Motivo
1. Melhor relaÃ§Ã£o entre **tempo curto** e **efeito de "quase vÃ­rus"**.
2. Permite entregar base funcional + escalonamento absurdo em 1 dia.
3. FÃ¡cil mostrar cÃ³digo tÃ©cnico sem parecer sÃ³ "chat com LLM".

### Como usar na prÃ¡tica (MVP)
1. `main.py`: loop principal + mÃ¡quina de estados.
2. `monitor.py`: janela ativa/processo ativo.
3. `policy.py`: lista de apps produtivos e regras.
4. `enforcer.py`: fechar/minimizar app + overlay topmost.
5. `rest_mode.py`: abrir vÃ­deos/sons/alerta piscante.
6. `schedule.py`: escalonamento (1, 3, 5, 8, 13... atÃ© 42 min).
7. `logs.jsonl`: trilha para narrar na apresentaÃ§Ã£o.

### Exemplo de escalonamento
| Ciclo | Descanso | Produtividade liberada | IntervenÃ§Ã£o |
|---|---|---|---|
| 1 | 1 min | 6 min | 1 vÃ­deo relaxante |
| 2 | 3 min | 6 min | overlay piscando leve |
| 3 | 5 min | 5 min | 2 vÃ­deos curtos sequenciais |
| 4 | 8 min | 5 min | alerta "dopamina crÃ­tica" |
| 5 | 13 min | 4 min | 2 vÃ­deos simultÃ¢neos |
| 6 | 21 min | 3 min | popup + Ã¡udio ambiente |
| 7 | 34 min | 2 min | 3 vÃ­deos curtos |
| 8+ | 42 min (teto) | 2 min | modo caos mÃ¡ximo |

---

## EntregÃ¡vel viÃ¡vel em 1 dia
1. Monitora VS Code/terminal/planilha.
2. Bloqueia quando em descanso.
3. ForÃ§a vÃ­deo + overlay de alerta.
4. Libera janela curta de produtividade.
5. Escala automaticamente atÃ© 42 min.
6. Gera logs para provar funcionamento no vÃ­deo demo.

---

## ObservaÃ§Ãµes tÃ©cnicas importantes
1. Para hackathon, foquem em bloqueio de alto impacto visual; nÃ£o tentem proteÃ§Ã£o anti-bypass real.
2. Se evento WMI der fricÃ§Ã£o, usem polling frequente de janela/processo (mais simples e suficiente para demo).
3. Tratem isso como ferramenta satÃ­rica de bem-estar para evitar leitura negativa.

---

## ReferÃªncias oficiais Ãºteis
1. `GetForegroundWindow` (Win32): https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getforegroundwindow
2. `SetForegroundWindow` (restriÃ§Ãµes): https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setforegroundwindow
3. `Win32_ProcessStartTrace` (WMI): https://learn.microsoft.com/en-us/previous-versions/windows/desktop/krnlprov/win32-processstarttrace
4. Wayland security model (isolamento entre clientes): https://wayland.freedesktop.org/docs/html/ch04.html
5. `xdotool` manual (X11 automaÃ§Ã£o): https://manpages.debian.org/bookworm/xdotool/xdotool.1.en.html
6. PyInstaller usage: https://pyinstaller.org/en/latest/usage.html


