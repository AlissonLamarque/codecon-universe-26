# Anti-Burnout

Anti-Burnout é um app Windows para reduzir recaídas de produtividade em momentos
de descanso. Ele monitora a janela ativa, identifica apps de alto risco produtivo
e conduz o usuário de volta para pausas guiadas antes que a situação evolua para
mais uma sessão desnecessária de VS Code às 23h.

A proposta é simples: se ferramentas de foco ajudam você a trabalhar melhor, o
Anti-Burnout ajuda você a parar melhor. A diferença é que ele leva essa missão
com uma seriedade talvez excessiva.

Ele funciona como um Pomodoro reverso: o descanso é o padrão, a produtividade é
liberada em pequenas janelas controladas, e tentativas fora do horário recebem
intervenções graduais. Na primeira vez, o sistema recomenda uma pausa. Na segunda,
ele entende como reincidência. A partir daí, desobedecer ao descanso pode gerar
mais alertas, mais redirecionamentos e uma postura cada vez menos negociável.

## Recursos

- monitoramento da janela ativa no Windows;
- ciclos automáticos de descanso e produtividade;
- contenção de apps produtivos durante pausas obrigatórias;
- abertura de conteúdo relaxante com fallback local;
- mensagens contextuais que escalam conforme a insistência;
- modo pânico para demonstrações e intervenções mais rápidas;
- tray icon com controles em tempo real;
- logs para acompanhar bloqueios, alertas e sessões de descanso.

## Como O Sistema Se Comporta

O Anti-Burnout começa educado. Ele avisa, orienta e oferece conteúdo relaxante.
Isso funciona bem para usuários que aceitam o descanso como uma recomendação
técnica razoável.

Se o usuário insiste em voltar para apps produtivos durante o descanso obrigatório,
o sistema registra a reincidência e aumenta o tom da intervenção. O objetivo não
é punir; é preservar a pausa mesmo quando o usuário claramente perdeu a capacidade
de tomar boas decisões envolvendo planilhas, terminais ou IDEs.

Em resumo: siga o fluxo de descanso e tudo permanece civilizado. Desobedeça o
sistema repetidas vezes e ele assume que você precisa de supervisão mais ativa.

## Instalação Rápida

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Rodar

```powershell
python main.py
```

Ao iniciar, o app abre um launcher com perfis de uso:


1. `Dev safe`: modo seguro para desenvolvimento, sem bloquear VS Code/terminal.
2. `Live normal`: aplica contenção durante períodos de descanso.
3. `Panic demo`: força intervenção quando o VS Code entra em foco.
4. `Alert Message Mode`: usa frases locais ou Ollama para alertas dinâmicos.

## Controles No Tray

Depois de iniciado, o app fica na bandeja do Windows.

1. `Ativo`: liga/desliga intervenções, notificações e mídia relaxante.
2. `Modo dev`: evita bloquear o ambiente de desenvolvimento.
3. `Modo pânico`: força intervenção quando o VS Code aparece.
4. `Notificações`: liga/desliga alertas sem reiniciar o app.
5. `Sair`: encerra o app.


## Alertas

Por padrão, o Anti-Burnout usa frases locais, rápidas e estáveis. Esse modo é
recomendado para demonstrações.

Para mensagens dinâmicas com LLM local, instale o Ollama e rode:

```powershell
ollama pull qwen2.5:1.5b-instruct

$env:AB_ENABLE_LLM_ALERTS="1"
$env:AB_ALERT_BACKEND="ollama"
$env:AB_OLLAMA_MODEL="qwen2.5:1.5b-instruct"
python main.py
```

Se o LLM falhar, demorar ou não estiver disponível, o app volta automaticamente
para as frases locais. A fiscalização do descanso não depende de internet para
continuar funcionando.

## Flags Úteis

```powershell
python main.py --no-launcher --profile dev
python main.py --no-launcher --profile live
python main.py --no-launcher --profile panic
python main.py --no-launcher --live --no-notifications
```

## Gerar Executável

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name AntiBurnout --add-data "assets;assets" main.py
```

Saída:

```text
dist\AntiBurnout.exe
```

Ao abrir o executável, o launcher aparece primeiro para escolher o perfil de
contenção.

## Filosofia

O Anti-Burnout parte de uma premissa operacional: descanso não deve ser tratado
como interrupção da produtividade, e sim como o estado que precisa ser protegido.

Produtividade continua disponível. Só precisa esperar a própria janela. Caso não
espere, o sistema está autorizado, por design, a ser inconvenientemente zeloso.
