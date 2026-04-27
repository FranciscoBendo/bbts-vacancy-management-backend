# BBTS — Gestão de Vagas · Backend

API REST com IA para extração de currículos, normalização por sinônimos e ranking explicável de candidatos.  
Stack: **FastAPI · PostgreSQL · SQLAlchemy · Alembic · Docker · Google Gemini**

---

## Pré-requisitos

- Docker + Docker Compose
- Chave da API do Google Gemini → [aistudio.google.com](https://aistudio.google.com) (gratuita)

---

## Instalação e execução

```bash
# 1. Clone o repositório
git clone https://github.com/cauagomesdev/bbts-vacancy-management-backend.git
cd bbts-vacancy-management-backend

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e preencha GEMINI_API_KEY=sua-chave-aqui

# 3. Suba tudo
docker compose up --build
```

**API:** http://localhost:8000  
**Swagger:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

---

## Rodar localmente (sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # ajuste DATABASE_URL e GEMINI_API_KEY
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

---

## Migrations e Seed

```bash
# Aplicar todas as migrations
docker compose exec api alembic upgrade head

# Popular banco com dados de demonstração (executar uma vez)
docker compose exec api python seed.py

# Resetar dados a qualquer momento
docker compose exec api python seed.py
```

---

## Estrutura de pastas

```
app/
├── main.py                  # FastAPI app, CORS, routers
├── config.py                # Settings via .env (inclui GEMINI_API_KEY)
├── database.py              # Engine + SessionLocal
├── models.py                # Todos os modelos SQLAlchemy
├── auth/                    # Login fake JWT · guards
├── vacancies/               # CRUD vagas + submit
├── approvals/               # Approve/Reject (RH) + dispara scoring
├── candidates/              # Ranking por vaga + listagem + detalhe
├── imports/
│   ├── pdf_extractor.py     # Integração Google Gemini (leitura de PDF)
│   ├── service.py           # Import PDF/CSV/JSON + normalização sinônimos
│   └── router.py            # Endpoints de importação
├── scoring/
│   └── engine.py            # Motor de score (peso + obrigatórios + localização)
├── synonyms/
│   └── dictionary.py        # Dicionário fixo de sinônimos (JS→javascript, etc.)
└── connectors/
    └── base.py              # ProfileConnector — interface para Sprint futura
alembic/
└── versions/
    ├── 001_initial.py       # Sprint 1: users, vacancies, requirements, approvals, audit
    ├── 002_sprint2.py       # Sprint 2: candidates (rico), integration_logs
    └── 003_sprint3.py       # Sprint 3: no-op (sinônimos são em código)
```

---

## Endpoints

### Auth
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/auth/login` | Login com `{ "user_id": 1 }` | Todos |
| GET | `/auth/me` | Usuário autenticado | Todos |

### Vagas
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies` | Listar vagas | REQUESTER (só suas) / RH (todas) |
| POST | `/vacancies` | Criar vaga + requisitos | Todos |
| GET | `/vacancies/:id` | Detalhe + requisitos | Todos |
| PATCH | `/vacancies/:id` | Editar (apenas DRAFT) | Todos |
| POST | `/vacancies/:id/submit` | Submeter para aprovação | REQUESTER |

### Aprovações
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/approvals/pending` | Vagas aguardando aprovação | RH |
| POST | `/approvals/:id/approve` | Aprovar + calcular scores | RH |
| POST | `/approvals/:id/reject` | Recusar (justificativa obrigatória) | RH |

### Candidatos
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| GET | `/vacancies/:id/candidates` | Ranking por vaga (score desc) | Todos |
| GET | `/candidates` | Listar candidatos (filtros: skill, location) | Todos |
| GET | `/candidates/:id` | Perfil completo do candidato | Todos |

### Importação
| Método | Rota | Descrição | Role |
|--------|------|-----------|------|
| POST | `/candidates/import/pdf` | Upload PDF → Gemini extrai → salva | RH |
| POST | `/candidates/import/json` | Import em lote via JSON | RH |
| POST | `/candidates/import/csv` | Import em lote via CSV | RH |
| GET | `/candidates/import/template` | Baixar template CSV | RH |

---

## Fluxo de demo

### 1. Login como REQUESTER
```http
POST /auth/login
{ "user_id": 1 }
```

### 2. Criar e submeter vaga
```http
POST /vacancies
Authorization: Bearer <token>

{
  "title": "Dev Backend Sênior",
  "description": "Squad de pagamentos.",
  "location": "São Paulo, SP",
  "priority": "HIGH",
  "requirements": [
    { "type": "SKILL", "name": "Python", "weight": 3.0, "mandatory": true },
    { "type": "LANGUAGE", "name": "Inglês", "weight": 1.0, "mandatory": false }
  ]
}

POST /vacancies/{id}/submit
```

### 3. Login como RH, importar currículo PDF e aprovar vaga
```http
POST /auth/login
{ "user_id": 2 }

POST /candidates/import/pdf
Authorization: Bearer <token_rh>
Content-Type: multipart/form-data
file: curriculo.pdf
```
> O Gemini extrai automaticamente todos os dados do currículo.

```http
POST /approvals/{id}/approve
Authorization: Bearer <token_rh>
{ "justification": "Perfil aprovado." }
```
> Ao aprovar, o sistema calcula o score de **todos os candidatos** contra os requisitos da vaga.

### 4. Ver ranking
```http
GET /vacancies/{id}/candidates
GET /candidates?skill=python&location=São Paulo
```

---

## Motor de Score

```
score_base     = (peso_atendido / peso_total) × 100
penalidade_req = qtd_obrigatórios_ausentes × 30%
penalidade_loc = 10% se localização não bate
score_final    = score_base × (1 - penalidade_req) × (1 - penalidade_loc)
```

Matching normalizado via dicionário de sinônimos antes da comparação.

---

## Dicionário de Sinônimos

Localizado em `app/synonyms/dictionary.py`. Para adicionar:

```python
SYNONYMS = {
    "js": "javascript",
    "k8s": "kubernetes",
    "sua-variacao": "termo-canonico",
}
```

Aplicado automaticamente na ingestão (PDF, CSV, JSON) e no motor de score.

---

## Formato CSV para importação

```
full_name,headline,email,location,linkedin_url,skills,languages,certifications,education,experiences
João Silva,Dev Backend,joao@email.com,São Paulo SP,,Python:Avançado:5;FastAPI:Inter:2,Inglês:B2,AWS:Amazon:2023,USP:CC:Bach:2018,BBTS:Dev:2022:2024:false
```

Campos compostos: `;` separa itens, `:` separa sub-campos internos.

---

## Usuários do seed

| id | Nome | Email | Role |
|----|------|-------|------|
| 1 | Ana Souza | ana@bbts.com | REQUESTER |
| 2 | Carlos RH | carlos@bbts.com | RH |

## Vagas do seed

| id | Título | Status |
|----|--------|--------|
| 1 | Desenvolvedor Frontend Sênior | DRAFT |
| 2 | Engenheiro de Dados Pleno | PENDING_APPROVAL |
| 3 | Tech Lead Backend (Java / Spring) | APPROVED + scores calculados |

## Candidatos do seed (6)

Rodrigo Almeida · Fernanda Lima · Bruno Martins · Juliana Costa · Lucas Ferreira · Camila Rocha

---

## Próximas sprints

- [ ] Sprint 4: Role MANAGER, dashboard de KPIs por vaga
- [ ] Sprint 5: Conectores externos (Gupy, EmpregaNet) via `ProfileConnector`
- [ ] Sprint 6: SSO / autenticação real, busca semântica com pgvector
