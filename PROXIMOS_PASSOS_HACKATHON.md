# MALARQ MALARQ MALARQ

# Próximos Passos MALARQ VEJA - Anti-Burnout (Hackathon)

## Objetivo deste documento
Organizar as próximas tarefas do projeto para execução rápida em equipe, com prioridade clara e orientação prática de implementação.

---

## Status atual (resumo)
1. App roda com tray icon.
2. Tem launcher inicial (perfil Dev/Live/Panic).
3. Durante descanso, app minimiza apps produtivos e abre vídeo relaxante.
4. Modo pânico já existe (intervenção mais agressiva no VSCode).
5. Flags principais já são alteráveis no tray (`Ativo`, `Modo dev`, `Modo pânico`, `No overlay`).

---

## Sobre o "painel ao vivo" (explicação rápida)
Painel ao vivo = uma janelinha própria do app (ex.: Tkinter) que mostra:
1. fase atual (`DESCANSO` / `PRODUTIVIDADE`);
2. tempo restante atualizando a cada 1s;
3. ciclo e modo ativo.

### Por que isso existe
O menu da bandeja (`pystray`) no Windows se comporta como snapshot quando está aberto; não atualiza texto em tempo real de forma confiável enquanto o menu fica expandido.

### Prioridade
**Baixa prioridade no momento.**  
Não é bloqueador para demo nem para funcionamento principal.

---

## Backlog priorizado

## P0 - Essencial para demo do hackathon

### 1) Intervenção consistente ao retornar para app produtivo no descanso
**O que fazer**  
Garantir que, toda vez que usuário voltar para VSCode (ou outro produtivo) durante descanso:
1. minimiza de novo;
2. abre vídeo de novo (ou outro vídeo).

**Por que**  
É o comportamento central da ideia e precisa parecer inevitável na apresentação.

**Como fazer (técnico)**
1. manter cooldown curto no descanso;
2. checar janela ativa em polling;
3. se processo produtivo em `REST_FORCED`, disparar intervenção sempre.

**Status esperado para validação**
1. tentar abrir VSCode 5 vezes em sequência durante descanso;
2. deve minimizar e redirecionar todas as vezes.

---

### 2) Robustez de abertura de vídeo
**O que fazer**  
Melhorar fallback quando YouTube falhar (rede lenta/sem resposta).

**Por que**  
Evita demo quebrada por internet.

**Como fazer (técnico)**
1. manter busca dinâmica para link `watch`;
2. se falhar, abrir URL de busca;
3. se falhar de novo, abrir mídia local (`assets/relax.mp4`).

**Status esperado para validação**
1. desligar internet e forçar intervenção;
2. app ainda mostra conteúdo de descanso local.

---

### 3) Script de validação rápida de demo
**O que fazer**  
Criar checklist/roteiro automático curto para ensaio.

**Por que**  
Ajuda equipe a repetir demo sem improviso.

**Como fazer (técnico)**
1. documento com sequência de clique;
2. blocos de fala para pitch;
3. tempo total 2-3 minutos.

---

## P1 - Melhorias importantes (mas não bloqueadoras)

### 4) Dificultar fuga fechando o vídeo
**O que fazer**  
Quando usuário fecha o vídeo e volta pro app produtivo durante descanso, reabrir conteúdo imediatamente (já parcialmente coberto).  
Evolução: rastrear se janela de distração ainda está ativa.

**Por que**  
Aumenta o efeito "não tem escapatória" sem destruir processos.

**Como fazer (técnico)**
1. guardar timestamp e quantidade de redirecionamentos por ciclo;
2. se detectar retorno produtivo em menos de X segundos, abrir 2 vídeos ao invés de 1;
3. opcional: usar player dedicado em tela cheia ao invés de browser.

**Risco**
1. exagero pode irritar demais durante desenvolvimento.
2. manter kill switch no tray é obrigatório.

---

### 5) Mensagens meme dinâmicas (sem LLM, versão rápida)
**O que fazer**  
Mostrar frases engraçadas no overlay antes de usar LLM.

**Por que**  
Entrega impacto cômico imediato com baixo risco técnico.

**Como fazer (técnico)**
1. lista local de mensagens;
2. selecionar por ciclo, aleatório ou por intensidade;
3. exibir junto do overlay.

Exemplos:
1. "Produtividade detectada. Isso é perigoso para sua paz interior."
2. "Seu cérebro pediu férias e você abriu o VSCode."
3. "Descanso compulsório ativado pelo Ministério da Dopamina."

---

### 6) Métricas para vender na apresentação
**O que fazer**  
Gerar resumo de logs (`events.jsonl`) com números de impacto.

**Por que**  
Dá "cara de produto sério" para a piada.

**Como fazer (técnico)**
1. script `report.py` lendo logs;
2. total de bloqueios, ciclos e minutos de descanso;
3. imprimir "Índice de Overwork Evitado".

---

## P2 - Evoluções avançadas

### 7) Mensagens geradas por LLM (fase futura)
**O que fazer**  
Integrar modelo de linguagem para gerar mensagens de intervenção em tempo real.

**Por que**  
Personaliza humor e deixa a demo mais impressionante.

**Como fazer (técnico)**
1. coletar contexto curto: fase, ciclo, tentativas recentes;
2. montar prompt com tom meme/anti-burnout;
3. gerar frase curta (1-2 linhas) para overlay;
4. fallback local se API falhar.

**Riscos**
1. dependência de internet/API;
2. custo/latência;
3. conteúdo imprevisível sem moderação de prompt.

**Mitigação**
1. modo offline com frases prontas;
2. timeout curto e fallback automático.

---

### 8) Painel ao vivo de status (tempo em tempo real)
**O que fazer**  
Criar janela de status com contagem regressiva ao vivo.

**Por que**  
Contorna limitação visual do menu da bandeja.

**Como fazer (técnico)**
1. janela Tkinter pequena (`always on top` opcional);
2. atualizar a cada 1000 ms com `after`;
3. exibir fase, restante, ciclo e modos.

### Prioridade desta tarefa
**Baixa** (não bloquear implementação principal nem demo).

---

## Sequência recomendada para o próximo turno de trabalho
1. Fechar P0.1 (intervenção repetida no descanso).
2. Fechar P0.2 (fallback de vídeo local).
3. Fechar P1.5 (mensagens meme locais).
4. Fechar P1.6 (script de métricas).
5. Só depois considerar P2.8 (painel ao vivo).

---

## Critério de "pronto para apresentação"
1. Launcher abre e inicia sem terminal.
2. Tray permite controlar modos sem reiniciar.
3. Durante descanso, VSCode é minimizado e usuário é redirecionado sempre.
4. Demo funciona mesmo com internet instável.
5. Existe roteiro + números de impacto para pitch final.

