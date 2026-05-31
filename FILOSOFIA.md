# FILOSOFIA.md

# A Visão Técnica do Pomodoro Reverso

> *"Se todo app tenta te fazer produzir mais, este tenta te impedir antes que seja tarde."*

O Anti-Burnout nasceu de uma desconfiança básica: talvez o usuário não devesse
ter acesso irrestrito ao próprio VS Code.

A maioria dos apps de produtividade promete foco, metas, dashboards e aquela
culpa premium embalada como evolução pessoal. A gente fez o caminho contrário.
Se o usuário tenta trabalhar, o sistema interpreta como sinal de alerta. Se tenta
de novo, vira reincidência. Se insiste, bom, alguém precisa assumir o controle.

Não é um timer. É um pequeno fiscal de descanso rodando no Windows, olhando a
janela ativa e julgando silenciosamente suas escolhas.

---

## Premissa Operacional

A regra normal é: trabalhe bastante, descanse um pouco, volte melhor.

A nossa é: descanse por padrão; se for trabalhar, peça licença ao sistema.

1. **Descanso é o estado inicial.**
   O app começa em `REST_FORCED` porque confiar no usuário logo de cara seria
   ingenuidade técnica.

2. **Trabalho é um evento suspeito.**
   IDE, terminal, planilha e editor de texto são tratados como sinais de que
   alguém está prestes a fazer uma escolha ruim.

3. **Insistência muda o tratamento.**
   Uma tentativa pode ser acidente. Duas já indicam hábito. Três pedem uma
   notificação com tom de repartição pública.

4. **O relaxamento também escala.**
   Se a pessoa continua tentando produzir, o sistema responde com mais descanso,
   mais vídeo relaxante e menos negociação.

---

## Arquitetura Como Crença

Cada módulo carrega um pedaço dessa lógica torta:

- `state_machine.py` decide se o usuário está em descanso obrigatório ou em
  liberdade produtiva temporária.

- `monitor.py` olha a janela ativa. Não basta o VS Code existir. O problema é
  você encarar ele com intenção.

- `policy.py` mantém a lista dos apps perigosos. É basicamente o código penal da
  produtividade.

- `enforcer.py` minimiza em vez de matar processos. A ideia é impedir o trabalho,
  não destruir o notebook de alguém no palco.

- `youtube_resolver.py` tenta abrir conteúdo relaxante. Porque bloquear o usuário
  e deixar ele olhando para o nada seria cruel demais até para este projeto.

- `alert_agent.py` começa educado e vai ficando mais autoritário conforme o
  usuário insiste em cometer produtividade.

- `logger_utils.py` registra tudo. Sem logs é só piada; com logs dá para fingir
  que existe uma métrica séria por trás.

---

## Princípios De Engenharia Questionável

1. **Parecer útil no começo.**
   O app precisa vender autocuidado por alguns segundos antes de revelar que
   autocuidado, aqui, é uma política de contenção.

2. **Intervir de verdade, mas sem quebrar nada.**
   Minimizar janela, abrir descanso e notificar já é irritante o suficiente.

3. **Usar configuração como dramaturgia.**
   `DEV_MODE`, `panic_mode`, cooldowns e ciclos existem para controlar o caos sem
   matar a demo.

4. **Funcionar mesmo quando a internet falha.**
   Se o YouTube não abrir, ainda existe `assets/relax.html`. O ócio não depende
   de CDN.

5. **Falar sério sobre uma ideia idiota.**
   O projeto funciona melhor quando se comporta como produto corporativo enquanto
   defende uma premissa completamente indefensável.

---

## Conclusão

O Anti-Burnout não resolve burnout. Seria muito ousado para um app que abre vídeo
de natureza como medida cautelar.

Ele resolve uma coisa bem menor e muito mais inútil: impedir que alguém trabalhe
quando um software decidiu que já deu.

Se o usuário terminou a sessão sem produzir nada, deu certo. Se alguém perguntou
"por que isso existe?", melhor ainda.

---

*Referências conceituais: Byung-Chul Han, Paul Lafargue, Bertrand Russell, Win32,
JSONL, janelas minimizadas e a suspeita permanente de que produtividade é apenas
procrastinação socialmente aceita.*
