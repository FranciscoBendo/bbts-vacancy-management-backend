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

```
app/
├── models.py                # User com password_hash · CandidateSuggestion com status de rejeição
├── auth/                    # register · login · JWT · bcrypt
├── vacancies/
│   └── router.py            # CRUD vagas + submit + rescore + GET /dashboard
├── approvals/               # scoring automático ao aprovar + rescore (preserva rejeições manuais)
├── candidates/
│   ├── service.py           # SCORE_THRESHOLD=40% · auto-rejeição · rejeição manual · anonimização LGPD
│   └── schemas.py           # CandidateListByVacancyOut · AnonymizeResponse
├── imports/                 # PDF (Groq) + CSV + JSON · detecção de duplicatas por e-mail
├── connectors/
│   ├── __init__.py
│   ├── base.py              # interface ProfileConnector para integrações futuras
│   ├── external.py          # conector randomuser.me
│   └── router.py            # POST /vacancies/:id/import-external
├── scoring/engine.py        # peso + obrigatórios + penalidade localização
├── synonyms/dictionary.py
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

```
Authorization: Bearer <token>
```

---

## Endpoints

### Auth
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/auth/register` | Cadastrar usuário | Público |
| POST | `/auth/login` | Login com email e senha | Público |
| GET | `/auth/me` | Usuário autenticado | Autenticado |

### Vagas
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies` | Listar | REQUESTER (só suas) / RH (todas) |
| POST | `/vacancies` | Criar + requisitos | Autenticado |
| GET | `/vacancies/:id` | Detalhe | Autenticado |
| PATCH | `/vacancies/:id` | Editar (só DRAFT) | Autenticado |
| POST | `/vacancies/:id/submit` | Submeter para aprovação | REQUESTER |
| POST | `/vacancies/:id/rescore` | Recalcular ranking | Autenticado |
| GET | `/vacancies/dashboard` | Indicadores gerais | Autenticado |

### Aprovações
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/approvals/pending` | Fila de pendentes | RH |
| POST | `/approvals/:id/approve` | Aprovar + calcular scores | RH |
| POST | `/approvals/:id/reject` | Recusar vaga | RH |

### Candidatos
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies/:id/candidates` | Ranking (score ≥ 40%) + recusados | Autenticado |
| POST | `/vacancies/:id/candidates/:suggestion_id/reject` | Recusar candidato manualmente | RH |
| GET | `/candidates` | Listar com filtros (skill, location) | Autenticado |
| GET | `/candidates/:id` | Perfil completo | Autenticado |
| DELETE | `/candidates/:id/anonymize` | Anonimizar dados pessoais (LGPD) | RH |

### Importação
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/candidates/import/pdf` | PDF → Groq extrai → verifica duplicata → salva | RH |
| POST | `/candidates/import/pdf/resolve` | Resolver duplicata após decisão do RH | RH |
| POST | `/candidates/import/json` | Import em lote JSON | RH |
| POST | `/candidates/import/csv` | Import em lote CSV | RH |
| GET | `/candidates/import/template` | Template CSV | RH |

### Conectores Externos
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/vacancies/:id/import-external` | Buscar candidatos externos (randomuser.me) | Autenticado |

---

## LGPD — Lei Geral de Proteção de Dados

O sistema implementa os seguintes mecanismos de conformidade com a Lei 13.709/2018:

### Anonimização de candidatos
`DELETE /candidates/:id/anonymize` remove os dados pessoais do candidato sem apagar o registro:

- Nome substituído por `Candidato Removido #ID`
- E-mail, LinkedIn e localização removidos
- Skills, experiências, formação, idiomas e certificações excluídos
- Histórico de scores no ranking mantido de forma anonimizada
- Ação registrada no log de auditoria com `action: CANDIDATE_ANONYMIZED_LGPD`

### Log de auditoria
Todas as ações sensíveis são registradas na tabela `audit_events` com: usuário responsável, ação realizada, entidade afetada e timestamp.

### Segurança dos dados
- Autenticação obrigatória em todas as rotas (JWT)
- Senhas armazenadas com hash bcrypt
- Anonimização restrita ao perfil RH

---

## Dashboard

`GET /vacancies/dashboard` retorna:

| Campo | Descrição |
|---|---|
| `total_vacancies` | Total de vagas cadastradas |
| `vacancies_by_status` | Contagem por status |
| `total_candidates` | Total de candidatos na base |
| `total_suggestions` | Total de sugestões ativas no ranking |
| `average_score` | Score médio dos candidatos ativos |
| `total_rejected_candidates` | Total de candidatos recusados (automático + manual) |

---

## Rejeição de candidatos

### Automática (score < 40%)
Candidatos abaixo de 40% são marcados como `REJECTED` automaticamente ao aprovar ou rescorar.

### Manual (RH)
O RH pode recusar qualquer candidato ativo com justificativa obrigatória. Rejeições manuais são **preservadas** ao atualizar o ranking.

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
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) (gratuito) |

---

## Próximas sprints

- [ ] Sprint 5: Role MANAGER com visão de área
- [ ] Sprint 6: Ranking explicativo por IA, busca semântica
- [ ] Sprint 7: SSO, conectores com Gupy e EmpregaNet