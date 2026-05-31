# FILOSOFIA.md

# A Visão Técnica do Pomodoro Reverso

> *"Se todo app tenta te fazer produzir mais, este tenta te impedir antes que seja tarde."*

O Anti-Burnout nasceu de uma desconfiança simples: talvez o usuário não devesse
ter acesso irrestrito ao próprio VS Code.

A maioria dos apps promete foco, metas, dashboards e a culpa premium de estar
sempre melhorando. A gente fez o contrário. Se o usuário tenta trabalhar no
momento errado, o sistema entende como sinal de risco. Se tenta de novo, vira
reincidência. Se insiste, o descanso deixa de ser sugestão e passa a ser política
de contenção.

Não é um timer. É um pequeno fiscal de descanso rodando no Windows, olhando a
janela ativa e julgando silenciosamente suas escolhas.

---

## A Tese

Epicuro defendia que uma vida boa não era uma vida lotada de estímulos, mas uma
vida com menos perturbação: tranquilidade, ausência de dor, desejos sob controle.

O Anti-Burnout concorda, mas do jeito errado.

Em vez de confiar que o usuário vai escolher a moderação, o app transforma essa
moderação em regra de sistema. O desejo de abrir uma IDE fora de hora vira um
impulso desnecessário. A janela produtiva vira tentação. O descanso vira o estado
que precisa ser protegido.

Bertrand Russell elogiou o ócio. Paul Lafargue defendeu o direito à preguiça.
Byung-Chul Han falou sobre a autoexploração disfarçada de realização pessoal.
Nós pegamos tudo isso, passamos por Win32, e chegamos à conclusão tecnicamente
suspeita de que minimizar janelas pode ser uma forma de cuidado.

---

## Premissa Operacional

A regra normal é: trabalhe bastante, descanse um pouco, volte melhor.

A nossa é: descanse por padrão; se for trabalhar, espere sua janela autorizada.

1. **Descanso é o estado inicial.**
   O app começa em `REST_FORCED` porque confiar no usuário logo de cara seria
   ingenuidade técnica.

2. **Trabalho é evento suspeito.**
   IDE, terminal, planilha e editor de texto são tratados como sinais de que
   alguém está prestes a negociar com a própria coluna.

3. **Insistência muda o tratamento.**
   Uma tentativa pode ser acidente. Duas indicam hábito. Três justificam uma
   postura mais administrativa.

4. **Relaxamento também escala.**
   Se a pessoa continua tentando produzir, o sistema responde com mais descanso,
   mais mensagem, mais vídeo e menos paciência.

---

## Arquitetura Como Crença

Cada módulo carrega um pedaço dessa lógica:

- `state_machine.py` define a moral do sistema: `REST_FORCED` protege o usuário;
  `PRODUCTIVE_WINDOW` concede liberdade provisória.

- `monitor.py` observa a janela ativa. Não basta o VS Code existir. O problema é
  você olhar para ele com intenção.

- `policy.py` mantém o código penal da produtividade. Ele decide quais processos
  merecem contenção e quais são protegidos para o app não se sabotar.

- `enforcer.py` minimiza em vez de matar processos. A meta é impedir trabalho,
  não destruir o notebook de alguém no palco.

- `youtube_resolver.py` abre conteúdo relaxante e usa fallback local. Nem falta
  de internet serve como desculpa para trabalhar.

- `alert_agent.py` dá voz ao sistema. Ele começa como app de bem-estar e vai
  ficando mais firme conforme o usuário insiste em cometer produtividade.

- `overlay.py` transforma descanso em evento visual. Popup, tela cheia e memes
  rotativos existem porque às vezes uma notificação educada não basta.

- `timer_overlay.py` deixa o ciclo sempre visível. É a placa na parede dizendo
  quanto falta para a liberdade produtiva voltar.

- `logger_utils.py` e `report.py` transformam o absurdo em evidência. Bloqueios,
  fugas, ciclos e o Índice de Overwork Evitado viram relatório, porque toda
  ideia duvidosa fica mais convincente quando ganha KPI.

---

## Decisões Que Assumimos

1. **O app precisa parecer produto real.**
   O launcher polido, o tray e o timer não estão ali só por acabamento. Eles
   fazem o sistema parecer legítimo antes de ele ficar inconvenientemente zeloso.

2. **A intervenção deve ser real, mas reversível.**
   Minimizar janela, focar o relaxamento e abrir overlays bastam. Destruir
   trabalho seria eficiente demais, e eficiência é justamente o vício que estamos
   tentando conter.

3. **Fuga também é dado.**
   Se o usuário sai do vídeo relaxante e volta para produtividade, o sistema não
   interpreta como preferência. Interpreta como reincidência documentável.

4. **A interface faz parte da punição terapêutica.**
   Popup antes do bloqueio, overlay de descanso e timer flutuante não são só UI.
   São rituais de transição entre "eu mando no computador" e "o computador acha
   que eu preciso respirar".

5. **Métrica corporativa vende qualquer delírio.**
   O relatório lê `events.jsonl` e produz indicadores como se o ócio fosse um
   OKR. Isso é importante: se o mundo mede produtividade, nós medimos a ausência
   dela com a mesma cara séria.

6. **Modo dev é confissão filosófica.**
   Para construir um app que bloqueia trabalho, precisamos de uma exceção que
   permita trabalhar. Chamamos isso de `DEV_MODE`; em filosofia moral, talvez
   fosse hipocrisia. Aqui é requisito funcional.

---

## Conclusão

O Anti-Burnout não tenta resolver burnout por completo. Isso seria muita
responsabilidade para um programa que abre vídeos de natureza como medida
cautelar.

Ele resolve uma coisa menor, mais específica e muito mais absurda: impedir que
alguém transforme qualquer minuto livre em oportunidade de produzir.

Epicuro queria menos perturbação. Russell queria mais ócio. Lafargue queria o
direito à preguiça. O Anti-Burnout quer tudo isso também, mas com tray icon,
logs, popup modal e um relatório executivo no final.

Se o usuário terminou a sessão sem produzir nada, o sistema funcionou.
Se alguém perguntou "por que isso existe?", melhor ainda.
