# Base do Programa Anti-Burnout: Opções Técnicas e Recomendação

## Objetivo deste documento
Este documento compara formas reais de implementar a base do programa anti-burnout (monitorar atividade, bloquear apps produtivos, forçar descanso e escalar o caos), com foco em **entregar algo filmável em 1 dia**.

## O que a base precisa fazer
1. Monitorar o que o usuário abre e usa (processo/janela em foco).
2. Detectar tentativa de uso de app produtivo (`Code.exe`, `idea64.exe`, `excel.exe`, `cmd.exe`, etc.).
3. Interromper/bloquear a tentativa.
4. Forçar descanso (overlay, alerta piscando, vídeos relaxantes).
5. Liberar uma janela curta de produtividade.
6. Repetir ciclos com escalonamento até o modo absurdo (descanso crescendo até 42 min + intervenções mais apelativas).

## Arquitetura base (independente da stack)
### Componentes
1. `Monitor`: observa processo/janela ativa.
2. `Policy Engine`: decide se o app é produtivo ou neutro.
3. `State Machine`: alterna entre `REST_FORCED` e `PRODUCTIVE_WINDOW`.
4. `Enforcer`: aplica bloqueio (kill/minimize/overlay/topmost).
5. `Distraction Orchestrator`: abre vídeos, sons, alertas e janelas.
6. `Escalation`: aumenta tempo e intensidade por ciclo.
7. `Logger`: grava eventos para demo e debug.

### Como o fluxo funciona
1. Usuário abre app produtivo.
2. Motor detecta evento em milissegundos/segundos.
3. Se o estado atual for descanso, bloqueia e dispara ritual de descanso.
4. Quando o descanso termina, libera produtividade por `N` minutos.
5. Ao vencer `N`, volta para descanso obrigatório com nível maior.

---

## Opções técnicas

## Opção A (recomendada): Python + pywin32 + psutil + overlay simples
### Como funciona
1. `pywin32` chama APIs Win32 para janela em foco.
2. `psutil` ajuda a identificar processos, PIDs e metadados.
3. Polling curto (ex.: 200-500 ms) verifica app em foco e estado.
4. `taskkill`/`TerminateProcess` fecha app bloqueado ou minimiza.
5. Overlay topmost (Tkinter/PySide) mostra alerta e bloqueio visual.
6. `subprocess` abre vídeos no player/navegador.

### Exemplo prático mínimo
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
1. Entrega rápida para hackathon.
2. Muito código pronto e curva de aprendizado baixa.
3. Fácil iterar regras absurdas sem recompilar toolchain pesada.
4. Boa para demo em vídeo.

### Pontos fracos
1. Não é blindado contra usuário avançado.
2. Controle de foco no Windows tem limitações (algumas mudanças de foco não obedecem sempre).
3. Pode exigir ajustes por versão/configuração do Windows.

### Quando escolher
Escolha esta opção se a meta for **MVP completo em 1 dia**.

---

## Opção B: C#/.NET (WPF/WinUI) + APIs Win32/WMI
### Como funciona
1. `ManagementEventWatcher` pode monitorar início de processo (WMI).
2. P/Invoke para APIs Win32 de janela/foco.
3. WPF cria overlay bonito/topmost facilmente.
4. Timers e state machine ficam em um serviço/app desktop robusto.

### Exemplo prático mínimo
```csharp
using System.Management;

var watcher = new ManagementEventWatcher(
    "SELECT * FROM Win32_ProcessStartTrace");

watcher.EventArrived += (s, e) =>
{
    var nome = e.NewEvent.Properties["ProcessName"]?.Value?.ToString();
    if (nome == "Code.exe")
    {
        // Exemplo: matar processo e abrir vídeo de descanso
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
1. Integração nativa forte com Windows.
2. Overlay/UI com acabamento superior.
3. Melhor estrutura para evoluir para produto real depois.

### Pontos fracos
1. Mais tempo de engenharia inicial.
2. Risco de perder tempo com detalhes de UI/build/publicação.
3. Para 1 dia, pode custar mais do que Python.

### Quando escolher
Se o time já domina C# e quer priorizar polish de desktop.

---

## Opção C: Electron/Node.js (desktop web)
### Como funciona
1. Processo principal monitora eventos e controla janelas da própria app.
2. Bibliotecas de terceiros tentam ler janela ativa/processos.
3. Bloqueio e overlays são feitos com `BrowserWindow` topmost.

### Exemplo prático mínimo
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
1. Time de frontend entrega interface divertida muito rápido.
2. Demo visual costuma ficar forte.

### Pontos fracos
1. Controle global de outras apps é menos direto que Win32 puro.
2. Dependência de libs externas pode gerar fricção.
3. Peso maior e mais variação de comportamento.

### Quando escolher
Se a demo depende muito de UI teatral e o controle agressivo pode ser "fakeado" no vídeo.

---

## Opção D: AutoHotkey + scripts auxiliares
### Como funciona
1. Hooks de hotkey/janela por script.
2. Regras de bloqueio e automação de janelas muito rápidas de testar.
3. Pode chamar PowerShell/Python para partes mais complexas.

### Exemplo prático mínimo
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
1. Protótipo extremamente rápido no Windows.
2. Muito bom para automação agressiva visível em demo.

### Pontos fracos
1. Manutenibilidade cai rápido com lógica complexa.
2. Escalação de features fica bagunçada.
3. Não passa tanto "arquitetura limpa" para avaliação de código.

### Quando escolher
Como plano B ultra-rápido, ou combinado com Python.

---

## Opção E: Linux X11 (Python + xdotool/wmctrl)
### Como funciona
1. `xdotool`/`wmctrl` manipulam foco e janelas no X11.
2. Scripts monitoram processo e aplicam bloqueios.
3. Overlay pode ser feito com Tkinter/PyQt.

### Exemplo prático mínimo
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
1. Automação global em X11 costuma ser permissiva.
2. Bom para efeitos "caóticos".

### Pontos fracos
1. Depende de sessão X11 (não Wayland).
2. Comportamento muda por window manager/distribuição.
3. Ambiente da demo precisa estar travado e previsível.

### Quando escolher
Se vocês controlam 100% o ambiente Linux e confirmam X11.

---

## Opção F: Linux Wayland (não recomendado para 1 dia)
### Como funciona
1. Wayland isola apps por design.
2. Controle global de outras janelas/processos é limitado sem caminhos especiais/portais/compositor-specific.

### Exemplo prático mínimo
```bash
# Em Wayland, o caminho típico passa por portais e consentimento do usuário.
# Isso já mostra por que é ruim para hackathon de 1 dia:
systemctl --user status xdg-desktop-portal.service
```

### Por que evitar agora
1. Grande risco técnico para prazo curto.
2. O comportamento varia bastante entre compositores.
3. Pode matar o hackathon por problemas de permissão/integração.

### Quando faria sentido
Projeto de pesquisa maior, sem prazo de 24h.

---

## Comparativo rápido (foco: 1 dia)
| Opção | Velocidade de entrega | Controle agressivo real | Risco técnico | Qualidade de demo |
|---|---|---|---|---|
| Python + pywin32 | Alta | Alta | Médio | Alta |
| C#/.NET | Média | Alta | Médio | Alta |
| Electron | Média | Média | Médio/Alto | Alta |
| AutoHotkey | Muito alta | Média/Alta | Médio | Média/Alta |
| Linux X11 | Média | Alta | Médio | Alta |
| Linux Wayland | Baixa | Baixa/Média | Alto | Incerta |

---

## Executável no Windows ou script como serviço?
## Recomendação para o hackathon
1. Construam como **script Python rodando na sessão do usuário**.
2. No final, empacotem em **`.exe` com PyInstaller** (`--onefile --windowed`).
3. Se quiser iniciar automaticamente, usem **Task Scheduler no logon** ou pasta `Startup`.

### Por que não usar serviço Windows no MVP
1. Serviço roda em Session 0 e não é bom para UI interativa (overlay, popups, vídeos).
2. Vocês teriam que fazer 2 processos (serviço + agente de UI), o que aumenta muito o escopo em 1 dia.

### Comandos práticos
```powershell
# Instalar dependências
pip install pywin32 psutil

# Rodar MVP
python main.py

# Empacotar .exe
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

---

## Recomendação final para vocês
## Escolha: Python + pywin32 no Windows, rodando na sessão do usuário e empacotado como `.exe`
### Motivo
1. Melhor relação entre **tempo curto** e **efeito de "quase vírus"**.
2. Permite entregar base funcional + escalonamento absurdo em 1 dia.
3. Fácil mostrar código técnico sem parecer só "chat com LLM".

### Como usar na prática (MVP)
1. `main.py`: loop principal + máquina de estados.
2. `monitor.py`: janela ativa/processo ativo.
3. `policy.py`: lista de apps produtivos e regras.
4. `enforcer.py`: fechar/minimizar app + overlay topmost.
5. `rest_mode.py`: abrir vídeos/sons/alerta piscante.
6. `schedule.py`: escalonamento (1, 3, 5, 8, 13... até 42 min).
7. `logs.jsonl`: trilha para narrar na apresentação.

### Exemplo de escalonamento
| Ciclo | Descanso | Produtividade liberada | Intervenção |
|---|---|---|---|
| 1 | 1 min | 6 min | 1 vídeo relaxante |
| 2 | 3 min | 6 min | overlay piscando leve |
| 3 | 5 min | 5 min | 2 vídeos curtos sequenciais |
| 4 | 8 min | 5 min | alerta "dopamina crítica" |
| 5 | 13 min | 4 min | 2 vídeos simultâneos |
| 6 | 21 min | 3 min | popup + áudio ambiente |
| 7 | 34 min | 2 min | 3 vídeos curtos |
| 8+ | 42 min (teto) | 2 min | modo caos máximo |

---

## Entregável viável em 1 dia
1. Monitora VS Code/terminal/planilha.
2. Bloqueia quando em descanso.
3. Força vídeo + overlay de alerta.
4. Libera janela curta de produtividade.
5. Escala automaticamente até 42 min.
6. Gera logs para provar funcionamento no vídeo demo.

---

## Observações técnicas importantes
1. Para hackathon, foquem em bloqueio de alto impacto visual; não tentem proteção anti-bypass real.
2. Se evento WMI der fricção, usem polling frequente de janela/processo (mais simples e suficiente para demo).
3. Tratem isso como ferramenta satírica de bem-estar para evitar leitura negativa.

---

## Referências oficiais úteis
1. `GetForegroundWindow` (Win32): https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getforegroundwindow
2. `SetForegroundWindow` (restrições): https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setforegroundwindow
3. `Win32_ProcessStartTrace` (WMI): https://learn.microsoft.com/en-us/previous-versions/windows/desktop/krnlprov/win32-processstarttrace
4. Wayland security model (isolamento entre clientes): https://wayland.freedesktop.org/docs/html/ch04.html
5. `xdotool` manual (X11 automação): https://manpages.debian.org/bookworm/xdotool/xdotool.1.en.html
6. PyInstaller usage: https://pyinstaller.org/en/latest/usage.html


