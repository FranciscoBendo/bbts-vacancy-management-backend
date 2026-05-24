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
git clone https://github.com/cauagomesdev/bbts-vacancy-management-backend.git
cd bbts-vacancy-management-backend

cp .env.example .env
# Edite .env e preencha GROQ_API_KEY=sua-chave-aqui

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

Após rodar o seed, sincronize a sequence do banco para evitar conflito de IDs ao cadastrar novos usuários:

```bash
docker compose exec db psql -U bbts -d bbts -c "SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));"
```

Usuários criados pelo seed:

| E-mail | Senha | Role |
|--------|-------|------|
| ana@bbts.com | 123456 | REQUESTER |
| carlos@bbts.com | 123456 | RH |

---

## Estrutura de pastas

```
app/
├── main.py
├── config.py                # inclui GROQ_API_KEY
├── database.py
├── models.py                # User com password_hash
├── auth/
│   ├── router.py            # POST /auth/register · POST /auth/login · GET /auth/me
│   ├── service.py           # bcrypt hash/verify · JWT · guards
│   └── schemas.py           # RegisterRequest · LoginRequest · TokenResponse
├── vacancies/
├── approvals/               # dispara scoring automático ao aprovar + rescore manual
├── candidates/              # ranking com filtro de score mínimo + listagem + detalhe
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
├── 003_sprint3.py
└── 004_add_password.py      # adiciona password_hash à tabela users
```

---

## Endpoints

### Auth
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/auth/register` | Cadastrar novo usuário (nome, email, senha, role) | Público |
| POST | `/auth/login` | Login com email e senha | Público |
| GET | `/auth/me` | Dados do usuário autenticado | Autenticado |

### Vagas
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies` | Listar | REQUESTER (só suas) / RH (todas) |
| POST | `/vacancies` | Criar + requisitos | Autenticado |
| GET | `/vacancies/:id` | Detalhe | Autenticado |
| PATCH | `/vacancies/:id` | Editar (só DRAFT) | Autenticado |
| POST | `/vacancies/:id/submit` | Submeter para aprovação | REQUESTER |
| POST | `/vacancies/:id/rescore` | Recalcular ranking de candidatos | Autenticado |

### Aprovações
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/approvals/pending` | Fila de pendentes | RH |
| POST | `/approvals/:id/approve` | Aprovar + calcular scores automaticamente | RH |
| POST | `/approvals/:id/reject` | Recusar (justificativa obrigatória) | RH |

### Candidatos
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies/:id/candidates` | Ranking filtrado por score mínimo (score desc) | Autenticado |
| GET | `/candidates` | Listar com filtros (skill, location) | Autenticado |
| GET | `/candidates/:id` | Perfil completo | Autenticado |

### Importação
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/candidates/import/pdf` | PDF → Groq extrai → salva | RH |
| POST | `/candidates/import/json` | Import em lote JSON | RH |
| POST | `/candidates/import/csv` | Import em lote CSV | RH |
| GET | `/candidates/import/template` | Template CSV | RH |

---

## Autenticação

Todas as rotas (exceto `/auth/login` e `/auth/register`) exigem o header:

```
Authorization: Bearer <token>
```

O token é retornado no login e no cadastro.

---

## Motor de Score

```
score_base     = (peso_atendido / peso_total) × 100
penalidade_req = qtd_obrigatórios_ausentes × 40%
penalidade_loc = 10% se localização do candidato ≠ localização da vaga
score_final    = score_base × (1 - penalidade_req) × (1 - penalidade_loc)
```

### Rescore manual

O score é calculado automaticamente quando uma vaga é aprovada. Para recalcular o ranking após novos candidatos, use `POST /vacancies/:id/rescore`. Ele apaga as sugestões existentes e recalcula para todos os candidatos, sem duplicatas.

### Filtro de score mínimo

`GET /vacancies/:id/candidates` retorna apenas candidatos com score ≥ **40%**. A resposta inclui:

| Campo | Tipo | Descrição |
|---|---|---|
| `candidates` | `list` | Lista filtrada, ordenada por score desc |
| `total_before_filter` | `int` | Total antes da filtragem |
| `score_threshold` | `float` | Limiar aplicado (padrão: 40.0) |

---

## Fluxo de extração de PDF

```
PDF → pypdf extrai texto → Groq LLaMA 3.3 70B → JSON estruturado → normaliza sinônimos → banco
                                 ↓ se falhar
                    Fallback: extração por palavras-chave do texto
```

O sistema nunca retorna erro por falha da IA — o fallback garante que pelo menos nome, email e skills básicas sejam extraídos.

> **Nota:** campos `company` e `role` dentro de `experiences` são normalizados automaticamente — valores `null` são convertidos para string vazia, evitando erro 422.

---

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | String de conexão PostgreSQL |
| `SECRET_KEY` | Chave para assinar tokens JWT |
| `GROQ_API_KEY` | Chave do Groq — [console.groq.com](https://console.groq.com) (gratuito) |

---

## Próximas sprints

- [ ] Sprint 4: Dashboard de KPIs por vaga, role MANAGER
- [ ] Sprint 5: Ranking explicativo por IA, busca semântica
- [ ] Sprint 6: Conectores externos (Gupy, EmpregaNet), SSO