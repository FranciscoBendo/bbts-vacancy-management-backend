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

**API:** http://localhost:8000 | **Swagger:** http://localhost:8000/docs

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
docker compose exec db psql -U bbts -d bbts -c "SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));"
```

Usuários do seed: `ana@bbts.com / 123456` (REQUESTER) · `carlos@bbts.com / 123456` (RH)

---

## Estrutura de pastas

```text
app/
├── models.py                # User com password_hash · CandidateSuggestion com status de rejeição
├── auth/                    # register · login · JWT · bcrypt
├── vacancies/
├── approvals/               # scoring automático ao aprovar + rescore manual
├── candidates/
│   ├── service.py           # SCORE_THRESHOLD=40% · auto-rejeição · rejeição manual
│   └── schemas.py           # CandidateListByVacancyOut com rejected separados
├── imports/                 # PDF (Groq) + CSV + JSON · detecção de duplicatas por e-mail
│   ├── schemas.py           # DuplicateDetectedOut · ResolveDuplicateIn
│   ├── service.py           # check_duplicate_by_email · _import_and_log · _to_snake
│   └── router.py            # /import/pdf com detecção · /import/pdf/resolve com 3 ações
├── scoring/engine.py        # peso + obrigatórios + penalidade localização
├── synonyms/dictionary.py
└── connectors/base.py
alembic/versions/
├── 001_initial.py
├── 002_sprint2.py
├── 003_sprint3.py
├── 004_add_password.py
└── 005_candidate_rejection.py
```

---

## Autenticação

Todas as rotas (exceto `/auth/login` e `/auth/register`) exigem o header:

```text
Authorization: Bearer <token>
```

O token é retornado no login e no cadastro.

---

## Endpoints

### Auth

| Método | Rota | Descrição | Role |
| --- | --- | --- | --- |
| POST | `/auth/register` | Cadastrar usuário | Público |
| POST | `/auth/login` | Login com email e senha | Público |
| GET | `/auth/me` | Usuário autenticado | Autenticado |

### Vagas

| Método | Rota | Descrição | Role |
| --- | --- | --- | --- |
| GET | `/vacancies` | Listar | REQUESTER (só suas) / RH (todas) |
| POST | `/vacancies` | Criar + requisitos | Autenticado |
| GET | `/vacancies/:id` | Detalhe | Autenticado |
| PATCH | `/vacancies/:id` | Editar (só DRAFT) | Autenticado |
| POST | `/vacancies/:id/submit` | Submeter para aprovação | REQUESTER |
| POST | `/vacancies/:id/rescore` | Recalcular ranking | Autenticado |

### Aprovações

| Método | Rota | Descrição | Role |
| --- | --- | --- | --- |
| GET | `/approvals/pending` | Fila de pendentes | RH |
| POST | `/approvals/:id/approve` | Aprovar + calcular scores | RH |
| POST | `/approvals/:id/reject` | Recusar vaga | RH |

### Candidatos

| Método | Rota | Descrição | Role |
| --- | --- | --- | --- |
| GET | `/vacancies/:id/candidates` | Ranking (score ≥ 40%) + recusados | Autenticado |
| POST | `/vacancies/:id/candidates/:suggestion_id/reject` | Recusar candidato manualmente | RH |
| GET | `/candidates` | Listar com filtros (skill, location) | Autenticado |
| GET | `/candidates/:id` | Perfil completo | Autenticado |

### Importação

| Método | Rota | Descrição | Role |
| --- | --- | --- | --- |
| POST | `/candidates/import/pdf` | PDF → Groq extrai → verifica duplicata → salva | RH |
| POST | `/candidates/import/pdf/resolve` | Resolver duplicata após decisão do RH | RH |
| POST | `/candidates/import/json` | Import em lote JSON | RH |
| POST | `/candidates/import/csv` | Import em lote CSV | RH |
| GET | `/candidates/import/template` | Template CSV | RH |

---

## Rejeição de candidatos

### Automática (score < 40%)

Ao aprovar ou rescorar uma vaga, candidatos abaixo de 40% são marcados como `REJECTED` com justificativa gerada automaticamente.

### Manual (RH)

O RH pode recusar qualquer candidato ativo com justificativa obrigatória.

### Resposta do ranking

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `candidates` | `list` | Ativos com score ≥ 40%, ordenados por score desc |
| `rejected` | `list` | Recusados (automático ou manual) com justificativa |
| `total_before_filter` | `int` | Total antes da filtragem |
| `score_threshold` | `float` | Limiar aplicado (40.0) |

---

## Importação de currículos via PDF e detecção de duplicatas

O endpoint `POST /candidates/import/pdf` verifica se o e-mail extraído do currículo já está cadastrado no banco **antes de persistir qualquer dado**. Se uma duplicata for detectada, o endpoint retorna um objeto com `duplicate_detected: true` e os dados extraídos do PDF — nenhuma escrita é feita no banco neste momento.

O frontend exibe um alerta ao RH com três opções, enviadas para `POST /candidates/import/pdf/resolve`:

| `action` | Comportamento |
| --- | --- |
| `update` | Atualiza o candidato existente com os dados do novo PDF |
| `create_new` | Cria um novo candidato removendo o e-mail para evitar conflito de constraint UNIQUE |
| `cancel` | Não persiste nada — importação cancelada pelo usuário |

> **Nota:** campos `company` e `role` dentro de `experiences` são normalizados automaticamente — valores `null` são convertidos para string vazia, evitando erro 422.

---

## Motor de Score

```text
score_base     = (peso_atendido / peso_total) × 100
penalidade_req = qtd_obrigatórios_ausentes × 30%
penalidade_loc = 10% se localização do candidato ≠ localização da vaga
score_final    = score_base × (1 - penalidade_req) × (1 - penalidade_loc)
```

---

## Fluxo de extração de PDF

```text
PDF → pypdf extrai texto → Groq LLaMA 3.3 70B → JSON estruturado → normaliza sinônimos
                                 ↓ se falhar                               ↓
                    Fallback: extração por palavras-chave         verifica e-mail duplicado
                                                                           ↓
                                                          duplicata → retorna DuplicateDetectedOut
                                                          sem duplicata → persiste e retorna CandidateDetailOut
```

O sistema nunca retorna erro por falha da IA — o fallback garante que pelo menos nome, email e skills básicas sejam extraídos.

---

## Variáveis de ambiente

| Variável | Descrição |
| --- | --- |
| `DATABASE_URL` | String de conexão PostgreSQL |
| `SECRET_KEY` | Chave para assinar tokens JWT |
| `GROQ_API_KEY` | console.groq.com (gratuito) |

---

## Próximas sprints

- [ ] Sprint 5: Dashboard de KPIs por vaga, role MANAGER
- [ ] Sprint 6: Ranking explicativo por IA, busca semântica
- [ ] Sprint 7: Conectores externos (Gupy, EmpregaNet), SSO
