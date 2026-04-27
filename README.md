# BBTS — Gestão de Vagas · Backend

API REST com IA para extração de currículos, normalização por sinônimos e ranking explicável de candidatos.  
Stack: **FastAPI · PostgreSQL · SQLAlchemy · Alembic · Docker · Groq (LLaMA 3.3 70B)**

---

## Pré-requisitos

- Docker + Docker Compose
- Chave da API do **Groq** → [console.groq.com](https://console.groq.com) (gratuita, 14.400 req/dia)

---

## Instalação e execução

```bash
# 1. Clone o repositório
git clone https://github.com/cauagomesdev/bbts-vacancy-management-backend.git
cd bbts-vacancy-management-backend

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e preencha GROQ_API_KEY=sua-chave-aqui

# 3. Suba tudo
docker compose up --build
```

**API:** http://localhost:8000  
**Swagger:** http://localhost:8000/docs

---

## Rodar localmente (sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

---

## Migrations e Seed

```bash
docker compose exec api alembic upgrade head
docker compose exec api python seed.py
```

---

## Estrutura de pastas

```
app/
├── main.py
├── config.py                # inclui GROQ_API_KEY
├── database.py
├── models.py
├── auth/
├── vacancies/
├── approvals/               # dispara scoring automático ao aprovar
├── candidates/              # ranking + listagem com filtros + detalhe
├── imports/
│   ├── pdf_extractor.py     # Groq (LLaMA 3.3 70B) + fallback por palavras-chave
│   ├── service.py           # normalização de sinônimos em todas as ingestões
│   └── router.py
├── scoring/engine.py        # peso + obrigatórios + penalidade de localização
├── synonyms/dictionary.py   # dicionário fixo de sinônimos
└── connectors/base.py       # interface para integrações futuras
alembic/versions/
├── 001_initial.py
├── 002_sprint2.py
└── 003_sprint3.py
```

---

## Endpoints

### Auth
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/auth/login` | Login com `{ "user_id": 1\|2 }` | Todos |
| GET | `/auth/me` | Usuário autenticado | Todos |

### Vagas
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies` | Listar | REQUESTER (só suas) / RH (todas) |
| POST | `/vacancies` | Criar + requisitos | Todos |
| GET | `/vacancies/:id` | Detalhe | Todos |
| PATCH | `/vacancies/:id` | Editar (só DRAFT) | Todos |
| POST | `/vacancies/:id/submit` | Submeter para aprovação | REQUESTER |

### Aprovações
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/approvals/pending` | Fila de pendentes | RH |
| POST | `/approvals/:id/approve` | Aprovar + calcular scores | RH |
| POST | `/approvals/:id/reject` | Recusar (justificativa obrigatória) | RH |

### Candidatos
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies/:id/candidates` | Ranking por vaga (score desc) | Todos |
| GET | `/candidates` | Listar com filtros (skill, location) | Todos |
| GET | `/candidates/:id` | Perfil completo | Todos |

### Importação
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/candidates/import/pdf` | PDF → Groq extrai → salva | RH |
| POST | `/candidates/import/json` | Import em lote JSON | RH |
| POST | `/candidates/import/csv` | Import em lote CSV | RH |
| GET | `/candidates/import/template` | Template CSV | RH |

---

## Fluxo de extração de PDF

```
PDF → pypdf extrai texto → Groq LLaMA 3.3 70B → JSON estruturado → normaliza sinônimos → banco
                                 ↓ se falhar
                    Fallback: extração por palavras-chave do texto
```

O sistema nunca retorna erro por falha da IA — o fallback garante que pelo menos nome, email e skills básicas sejam extraídos.

---

## Motor de Score

```
score_base     = (peso_atendido / peso_total) × 100
penalidade_req = qtd_obrigatórios_ausentes × 30%
penalidade_loc = 10% se localização do candidato ≠ localização da vaga
score_final    = score_base × (1 - penalidade_req) × (1 - penalidade_loc)
```

---

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | String de conexão PostgreSQL |
| `SECRET_KEY` | Chave para assinar tokens JWT |
| `GROQ_API_KEY` | Chave do Groq — [console.groq.com](https://console.groq.com) (gratuito) |

---

## Seed

| id | Usuário | Role |
|----|---------|------|
| 1 | Ana Souza | REQUESTER |
| 2 | Carlos RH | RH |

| id | Vaga | Status |
|----|------|--------|
| 1 | Dev Frontend Sênior | DRAFT |
| 2 | Engenheiro de Dados Pleno | PENDING_APPROVAL |
| 3 | Tech Lead Backend (Java/Spring) | APPROVED + scores calculados |

---

## Próximas sprints

- [ ] Sprint 4: Dashboard de KPIs, role MANAGER
- [ ] Sprint 5: Ranking explicativo por IA, busca semântica
- [ ] Sprint 6: Conectores externos (Gupy, EmpregaNet), SSO
