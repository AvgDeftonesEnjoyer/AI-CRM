# CRM Leads Service

A backend service for managing leads through a cold-processing pipeline with AI-powered analysis, built with FastAPI + PostgreSQL.

---

## How the System Works

Leads enter the system from three sources (`scanner`, `partner`, `manual`) and move through two sequential pipelines:

**Cold Pipeline** → **Sales Pipeline**

```
Cold:  new → contacted → qualified → transferred → (lost)
Sales: new → kyc → agreement → paid → (lost)
```

Stage transitions are strictly enforced — no skipping, no going back, and terminal stages (`transferred`, `paid`, `lost`) cannot be changed.

A manager can request an AI analysis of any lead at any point. The AI score and recommendation are stored on the lead record and used as input for the manager's decision to transfer to sales.

---

## Where AI Is Used and Why

AI is used for **lead scoring and recommendation** — it reads the lead's current data and returns:

- A probability score (0.0–1.0)
- A recommended action (`transfer_to_sales`, `continue_nurturing`, `mark_as_lost`)
- A human-readable reason

This is an appropriate use of AI because:

1. The inputs (source, stage, activity, domain) map naturally to a "quality signal"
2. The output is advisory — not a direct action
3. A human manager decides whether to act on the recommendation

The AI is **deliberately constrained**: it cannot change stages, create sales, or override business rules. It only provides structured insight.

---

## What Data Is Sent to AI

Only the minimum required for a meaningful assessment:

| Field             | Why                                                       |
| ----------------- | --------------------------------------------------------- |
| `source`          | Partner leads typically convert better than scanner leads |
| `stage`           | Qualified leads are more mature than new ones             |
| `message_count`   | Activity signals engagement level                         |
| `business_domain` | Presence of a domain indicates a real use case            |

No PII, no internal IDs, no financial data.

---

## What Decisions the Human Makes

| Decision                             | Who                                    |
| ------------------------------------ | -------------------------------------- |
| Create a lead                        | Manager                                |
| Move lead through cold stages        | Manager                                |
| Request AI analysis                  | Manager (on demand)                    |
| Transfer lead to sales               | Manager (system enforces requirements) |
| Move sale through KYC/agreement/paid | Manager                                |

The system enforces **three hard rules** for transfer — all must pass:

1. Lead must be in `qualified` stage
2. AI score ≥ 0.6
3. Business domain must be set

Even if AI recommends `transfer_to_sales`, the system blocks transfer if the above conditions aren't met. This prevents AI from bypassing business rules.

---

## Bonus Features Included (Beyond Requirements)

- **JWT Authentication** — CRM shouldn't have open endpoints. Added basic `User` model and `/auth/token` login.
- **Rate limiting** — The AI endpoint (`/api/v1/leads/{id}/analyze`) is rate-limited to avoid accidental cost spikes/spamming the Anthropic API.
- **Secure Docker** — Dockerfile runs as a non-root user. No hardcoded secrets in the configurations.

## What I'd Add in a Real Project

- **RBAC (Roles)** — Differentiate between Manager and Sales rep roles.
- **Audit log** — every stage transition recorded with who/when.
- **Webhooks** — notify external systems on transfer.
- **AI feedback loop** — track which AI recommendations led to `paid` outcomes and retrain/tune.
- **Richer AI context** — add lead's message history summary, time-in-stage, previous lost reasons.
- **Background jobs** — auto-analyze stale leads with Celery/ARQ.
- **Soft delete** — don't lose data, just archive.
- **Multi-tenancy** — isolate leads per organization.

---

## Quick Start

### With Docker (recommended)

```bash
# Clone and enter the repo
git clone <repo-url>
cd crm-leads

# Configure environment
cp .env.example .env
# Optional: add ANTHROPIC_API_KEY to .env for real AI
# Without it, a rule-based mock is used automatically

# Start everything
docker compose up --build
```

API available at: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

---

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your local DB connection

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

---

## API Endpoints

### Leads

| Method  | Path                          | Description             |
| ------- | ----------------------------- | ----------------------- |
| `POST`  | `/api/v1/leads/`              | Create a new lead       |
| `GET`   | `/api/v1/leads/`              | List all leads          |
| `GET`   | `/api/v1/leads/{id}`          | Get a lead              |
| `PATCH` | `/api/v1/leads/{id}/stage`    | Update lead stage       |
| `POST`  | `/api/v1/leads/{id}/messages` | Increment message count |
| `POST`  | `/api/v1/leads/{id}/analyze`  | Run AI analysis         |
| `POST`  | `/api/v1/leads/{id}/transfer` | Transfer lead to sales  |

### Sales

| Method  | Path                       | Description       |
| ------- | -------------------------- | ----------------- |
| `GET`   | `/api/v1/sales/`           | List all sales    |
| `GET`   | `/api/v1/sales/{id}`       | Get a sale        |
| `PATCH` | `/api/v1/sales/{id}/stage` | Update sale stage |

---

## Example Workflow

```bash
# 1. Register and Login to get a token
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@crm.com", "password": "securepassword123"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin@crm.com&password=securepassword123" | jq -r .access_token)

# 2. Create a lead
curl -X POST http://localhost:8000/api/v1/leads/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "partner", "business_domain": "first"}'

# 3. Register some messages
curl -X POST http://localhost:8000/api/v1/leads/1/messages -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/v1/leads/1/messages -H "Authorization: Bearer $TOKEN"

# 4. Move through stages
curl -X PATCH http://localhost:8000/api/v1/leads/1/stage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage": "contacted"}'

curl -X PATCH http://localhost:8000/api/v1/leads/1/stage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage": "qualified"}'

# 5. Request AI analysis
curl -X POST http://localhost:8000/api/v1/leads/1/analyze -H "Authorization: Bearer $TOKEN"

# 6. Transfer to sales (if AI score >= 0.6)
curl -X POST http://localhost:8000/api/v1/leads/1/transfer -H "Authorization: Bearer $TOKEN"
```

---

## Run Tests

```bash
pytest -v
```

---

## Project Structure

```
crm-leads/
├── app/
│   ├── api/v1/          # HTTP layer (routes only, no business logic)
│   │   ├── leads.py
│   │   └── sales.py
│   ├── core/
│   │   ├── config.py    # Settings from environment
│   │   ├── database.py  # Async SQLAlchemy engine + session
│   │   └── exceptions.py
│   ├── models/
│   │   └── lead.py      # SQLAlchemy ORM models + stage transition maps
│   ├── schemas/
│   │   └── lead.py      # Pydantic request/response schemas
│   ├── services/
│   │   ├── ai_service.py    # AI integration (Claude API + mock fallback)
│   │   ├── lead_service.py  # Lead business logic
│   │   └── sale_service.py  # Sale business logic
│   └── main.py
├── alembic/             # Database migrations
├── tests/
│   └── test_services.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
