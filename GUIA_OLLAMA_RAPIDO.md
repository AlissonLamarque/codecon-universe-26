# Guia Rapido: Ollama no Anti-Burnout

Se quiser usar mensagens com LLM local (sem token da API), o caminho mais rapido e:

## 1) Instalar Ollama
Baixe e instale em: `https://ollama.com/download/windows`

Depois, abra um terminal novo e confirme:
```powershell
ollama --version
```

## 2) Baixar o modelo (uma vez)
```powershell
ollama pull qwen2.5:1.5b-instruct
```

## 3) Rodar o app com backend Ollama
```powershell
$env:AB_ENABLE_LLM_ALERTS="1"
$env:AB_ALERT_BACKEND="ollama"
$env:AB_OLLAMA_MODEL="qwen2.5:1.5b-instruct"
$env:AB_OLLAMA_BASE_URL="http://localhost:11434"
python main.py
```

## 4) Teste rapido de saude
```powershell
Invoke-WebRequest -Method POST -Uri http://localhost:11434/api/generate -ContentType "application/json" -Body '{"model":"qwen2.5:1.5b-instruct","prompt":"ok","stream":false}'
```

Se falhar, o app ainda pode rodar com `Frases prontas (local)` no launcher.
