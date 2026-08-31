# AutoBot — AI Automobile Assistant 🚗⚡

AutoBot is an intelligent, full-stack automobile assistant tailored for the **Indian car market**. Built using **Pydantic AI**, **Google Gemini 3.6 Flash**, **Gradio**, and **PostgreSQL**, AutoBot seamlessly handles car recommendations, diagnostics triage, service schedules, and financial EMI calculations in a single conversation.

---

## 🌟 Key Features

- **🧠 LLM-Led Multi-Intent Classification**: Dynamically classifies complex user requests into single or multiple intents (`buying`, `diagnostics`, `service`, `finance`, `general`) without rigid keyword routers.
- **🛡️ Safe Read-Only Tool Boundary**: The LLM uses parameterised Python tools to query PostgreSQL and perform math. The model never executes raw SQL or accesses DB credentials.
- **⚡ Real-Time Word-by-Word Streaming**: Uses Pydantic AI's event-driven streaming (`run_stream_events`) to stream response tokens directly to the Gradio web interface as they generate.
- **📊 Fact-Grounded Evidence**: Grounded in real catalogue data for Indian vehicles, verified common-issue records, standard service intervals, and deterministic EMI math.
- **🚨 Diagnostic Triage & Safety Policy**: Identifies critical vehicle hazards (brake/steering loss, overheating, smoke/fire) and prioritizes safety advice ("do not drive") over repair steps.
- **🗄️ PostgreSQL Persistence & History**: Multi-user account registration (PBKDF2-hashed passwords) with saved chat sessions and searchable conversation history.
- **⚡ Fast In-Memory TTL Cache**: 5-minute thread-safe in-memory cache (`TTLCache`) for read-heavy catalogue queries (~0ms cache hits).
- **🔍 RapidFuzz Fuzzy Fallback Engine**: Uses token-set ratio fuzzy matching to match natural-language symptom descriptions (e.g., *"car shaking at high speed"*) to database records.

---

## 🏗️ Architecture & Workflow

```text
 ┌─────────────────────────────┐       ┌──────────────────────────────────┐
 │    Gradio Web UI (:7860)    │       │    FastAPI REST/SSE API (:8000)   │
 │    (existing, unchanged)    │       │    POST /chat  POST /chat/sync    │
 │                             │       │    POST /auth/signup  /auth/login │
 │                             │       │    GET /sessions/{id}/history     │
 │                             │       │    GET /health                    │
 └──────────────┬──────────────┘       └─────────────────┬────────────────┘
                │  stream_chat_with_autobot()              │  stream/chat_with_autobot()
                └──────────────────┬───────────────────────┘
                                   ▼
                      ┌────────────────────────┐
                      │   Pydantic AI Agent    │
                      │   (Gemini 2.5 Flash)   │
                      └────────────┬───────────┘
                                   │ LLM-selected tools
                                   ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ Safe Tool Boundary (Parameterised SQL & Pure Math)                      │
 │  • record_intent_classification   • search_catalog_by_segment           │
 │  • search_catalog                 • search_catalog_by_fuel              │
 │  • search_catalog_by_budget       • search_known_issue                  │
 │  • get_vehicle                    • calculate_loan_emi                  │
 │  • get_standard_service_intervals                                       │
 └────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │  PostgreSQL + TTLCache │
                     │  (5-Min Per-Key Expiry)│
                     └────────────────────────┘
```

---

## 📁 Project Structure

```text
Auto-Bot/
├── main.py                     # Gradio entrypoint — launches UI on port 7860
├── api_server.py               # FastAPI entrypoint — launches REST API on port 8000
├── run_all.py                  # Dev convenience — starts both servers from one command
├── docker-compose.yml          # Docker Compose — PostgreSQL service for local dev
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
│
├── api/                        # ── FastAPI Layer ────────────────────────────────────
│   ├── app.py                  # FastAPI app factory, CORS, startup warm-up, routers
│   ├── schemas.py              # Pydantic request/response models
│   ├── dependencies.py         # asyncio.to_thread wrappers for sync DB calls
│   ├── logger.py               # Centralized logging configuration
│   └── routers/
│       ├── health.py           # GET /health
│       ├── chat.py             # POST /chat (SSE) + POST /chat/sync
│       ├── auth.py             # POST /auth/signup + POST /auth/login
│       └── sessions.py         # GET /sessions/{session_id}/history
│
├── agents/
│   └── automotive_agent.py     # Pydantic AI Agent, system prompt, 9 tools
│
├── tools/
│   └── car_tools.py            # DB query helpers & EMI math
│
├── db/
│   ├── connection.py           # ThreadedConnectionPool (min=2, max=10) & TTLCache
│   ├── queries.py              # Parameterised SQL queries
│   ├── fuzzy_queries.py        # RapidFuzz fuzzy search engine
│   ├── auth.py                 # PBKDF2 password hashing & user auth
│   └── migrate.py              # DDL schema migration & seed data loader
│
├── models/
│   └── schemas.py              # Pydantic domain models
│
├── ui/
│   ├── app.py                  # Gradio SPA UI
│   └── formatters.py           # Markdown formatters
│
└── data/
    └── seed.json               # Seed data for PostgreSQL
```

---

## 🏷️ Intent Categories & Tools

AutoBot classifies every request into one or more of the following **5 Intent Categories**:

| Intent | Description | Example Query |
|---|---|---|
| 🛒 **`buying`** | Recommendations, comparisons, budget & features | *"Suggest petrol SUVs under 15 Lakhs"* |
| 🔧 **`diagnostics`** | Fault symptoms, warning lights, drivability & safety | *"My car vibrates at high speeds, what's wrong?"* |
| 🔩 **`service`** | Maintenance schedules, parts replacement & costs | *"When should I change engine oil and brake pads?"* |
| 💰 **`finance`** | EMI calculations, loan tenure, down payment | *"Calculate EMI for a 10L loan for 5 years at 9%"* |
| 💬 **`general`** | EV policies, rules, insurance, and accessories | *"What are the government rules on EV subsidies?"* |

### Available Safe Tools:
- **`record_intent_classification`**: Records detected intent labels.
- **`search_catalog` / `search_catalog_by_budget` / `search_catalog_by_fuel` / `search_catalog_by_segment`**: Queries vehicle inventory based on specifications.
- **`get_vehicle`**: Direct partial name match lookup for specific models (e.g. *"Altroz"*).
- **`search_known_issue`**: Performs exact SQL match followed by RapidFuzz token matching for diagnostic symptoms.
- **`get_standard_service_intervals`**: Fetches standard service intervals and estimated replacement costs.
- **`calculate_loan_emi`**: Pure mathematical execution of monthly loan EMI, interest, and total payable amount.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+**
- **Docker Desktop** (for running PostgreSQL locally) — [Download here](https://www.docker.com/products/docker-desktop/)
- **Google Gemini API Key** — [Get a free key from Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/Auto-Bot.git
cd Auto-Bot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Database — PostgreSQL via Docker Compose (Recommended)

AutoBot ships with a `docker-compose.yml` that spins up a dedicated PostgreSQL 16 container with a
persistent named volume. This is the recommended approach for local development — no cloud account or
system-wide Postgres installation needed.

#### Start PostgreSQL

```bash
docker compose up -d
```

Docker will pull `postgres:16` (first run only, ~200 MB), create the database, user, and volume, and
start the container in the background.

#### Verify the container is healthy

```bash
docker compose ps
```

Expected output:
```
NAME               IMAGE         STATUS              PORTS
autobot-postgres   postgres:16   Up (healthy)        0.0.0.0:5433->5432/tcp
```

#### View live PostgreSQL logs

```bash
docker compose logs -f db
```

#### Daily workflow

```bash
docker compose up -d      # Morning — start Postgres
docker compose down       # Evening — stop Postgres (data is preserved)
docker compose down -v    # Fresh wipe — stops AND deletes all data
```

#### Inspect database values from terminal

```bash
# Open an interactive psql shell inside the container
docker exec -it autobot-postgres psql -U autobot -d autobot_db

# Inside psql:
\dt                                          -- list all tables
SELECT name, brand, segment FROM cars;       -- browse car catalog
SELECT id, username, email FROM users;       -- browse registered users
SELECT session_id, title FROM conversations; -- browse saved chats
\q                                           -- exit
```

```bash
# Or check row counts in one command (no psql shell needed)
docker exec autobot-postgres psql -U autobot -d autobot_db \
  -c "SELECT tablename, n_live_tup AS rows FROM pg_stat_user_tables ORDER BY rows DESC;"
```

> **Note on port**: The container maps Docker's internal port `5432` to your local port **`5433`**.
> This avoids conflicts if you also have a system-level PostgreSQL running on `5432`.

---

### 4. Environment Configuration

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Gemini API Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL — Docker Compose (port 5433 avoids clash with local Postgres on 5432)
DATABASE_URL=postgresql://autobot:autobot123@localhost:5433/autobot_db

# Optional overrides
GEMINI_MODEL=gemini-3.6-flash
LOG_LEVEL=INFO
```

> **Cloud alternative**: If you prefer Supabase, Neon, or Render instead of Docker,
> set `DATABASE_URL` to your cloud connection string and skip the `docker compose` step.

---

### 5. Database Setup & Migration

Run the migration script to create all 6 tables and seed the Indian car catalog:

```bash
python db/migrate.py
```

Expected output:
```
✅  Migration complete!
   • cars:              8 rows
   • common_issues:     5 rows
   • service_intervals: 10 rows
```

### 6. Launch the Application

#### Option A — Gradio UI only

```bash
python main.py
```

Open your browser at `http://localhost:7860`.

#### Option B — FastAPI REST/SSE API only

```bash
python api_server.py
```

API available at `http://localhost:8000` · Interactive docs at `http://localhost:8000/docs`.

#### Option C — Both servers together (recommended for development)

```bash
python run_all.py
```

Starts Gradio on `:7860` and FastAPI on `:8000` as separate processes. Press `Ctrl+C` to stop both.

---

### 6. FastAPI Quick Reference

| Method | Endpoint | Description |
|:--|:--|:--|
| `GET` | `/health` | Liveness check — DB + agent status |
| `POST` | `/chat` | SSE streaming chat |
| `POST` | `/chat/sync` | Non-streaming chat, returns full JSON |
| `POST` | `/auth/signup` | Register a new user |
| `POST` | `/auth/login` | Authenticate, returns user record |
| `GET` | `/sessions/{id}/history` | Load past conversation messages |

**Example — sync chat:**
```bash
curl -X POST http://localhost:8000/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me petrol SUVs under 15 lakhs"}'
```

**Example — SSE streaming:**
```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate EMI for 10L at 9% for 5 years"}'
```

---

## 🔄 End-to-End Request Lifecycle

1. **User Interaction**: User enters a prompt in the Gradio chat canvas (e.g., *"Show me petrol SUVs under 15L and calculate EMI for 10L loan for 5 years"*).
2. **Session Persistence**: If logged in, the user message is saved to PostgreSQL in the `chat_messages` table under the active `session_id`.
3. **Intent Classification**: Gemini executes `record_intent_classification(intents=["buying", "finance"])` as its mandatory first tool call.
4. **Tool Execution**: Gemini selects relevant evidence tools (`search_catalog_by_fuel`, `search_catalog_by_budget`, `search_catalog_by_segment`, `calculate_loan_emi`).
5. **Caching & DB Lookup**: Tool calls check `TTLCache` (~0ms hit). On miss, a connection is borrowed from `ThreadedConnectionPool` to query PostgreSQL.
6. **Streaming Generation**: As Gemini writes its final natural-language Markdown output, `Pydantic AI` emits `PartDeltaEvent` tokens which stream to the UI in real time.
7. **Completion & Logging**: The complete answer, elapsed time, and intent labels are persisted to PostgreSQL and rendered with an execution badge (`⚡ Gemini 3.6 Flash · ⏱️ 1.4s`).

---

## 🛠️ Technology Stack

- **Language**: Python 3.10+
- **AI Framework**: [Pydantic AI](https://ai.pydantic.dev/)
- **LLM Engine**: Google Gemini 3.6 Flash (`google-genai`)
- **Web UI**: [Gradio](https://www.gradio.app/)
- **Database**: PostgreSQL (`psycopg2-binary`)
- **Fuzzy Search**: [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)
- **Environment**: `python-dotenv`

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).
