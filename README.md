# Egyptian Civil Code Legal RAG API

Production bilingual Arabic Legal Q&A service over the Egyptian Civil Code (Law of 1948).

## 3-Command Quickstart

```bash
# 1. Reproduce pipeline and extract corpus with DVC
dvc repro

# 2. Build and start the containerized service
docker compose up --build -d

# 3. Query the legal assistant
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "ما هو أثر العقد بين المتعاقدين؟", "top_k": 2}'

## Requirement


## Optional : Setup your terminal
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "

