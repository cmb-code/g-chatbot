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
                               ┌──────────────────────────┐
                               │   Gradio Web UI (7860)   │
                               └────────────┬─────────────┘
                                            │ Streams response tokens
                                            ▼
                               ┌──────────────────────────┐
                               │ Pydantic AI Agent        │
                               │ (Gemini 3.6 Flash)       │
                               └────────────┬─────────────┘
                                            │ Calls LLM-selected tools
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Safe Tool Boundary (Parameterised SQL & Pure Math)                                     │
│                                                                                        │
│  • record_intent_classification    • search_catalog_by_segment   • get_vehicle          │
│  • search_catalog                  • search_catalog_by_fuel      • search_known_issue   │
│  • search_catalog_by_budget        • calculate_loan_emi          • get_service_intervals│
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │  PostgreSQL + TTL Cache  │
                               │  (5-Min Per-Key Expiry)  │
                               └──────────────────────────┘
```

---

## 📁 Project Structure

```text
Auto-Bot/
├── main.py                     # Entry point — launches Gradio app on ports 7860–7869
├── requirements.txt            # Python dependencies (pydantic-ai, google-genai, gradio, etc.)
├── .env.example                # Template for environment configuration
│
├── agents/
│   └── automotive_agent.py     # Pydantic AI Agent setup, system prompt, and 8 evidence tools
│
├── tools/
│   └── car_tools.py            # Helper wrappers for DB queries and loan EMI math
│
├── db/
│   ├── connection.py           # ThreadedConnectionPool (min=2, max=10) & TTLCache
│   ├── queries.py              # Parameterised SQL queries for cars, issues, service & chat
│   ├── fuzzy_queries.py        # RapidFuzz fuzzy search engine & synonym/alias maps
│   ├── auth.py                 # User signup, login & PBKDF2 password hashing
│   └── migrate.py              # DDL schema migration & seed data loader
│
├── models/
│   └── schemas.py              # Pydantic domain models (QueryPlan, FuzzyCarFilter)
│
├── ui/
│   ├── app.py                  # Gradio UI components, theme CSS, auth & event wiring
│   └── formatters.py           # Markdown response formatters and card generators
│
└── data/
    └── seed.json               # Seed database for catalogue cars, issues, and service items
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
- **PostgreSQL Database** (Local or Cloud — e.g. Supabase, Neon, Render)
- **Google Gemini API Key** (Get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey))

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

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
# Gemini API Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL Connection String (Required)
DATABASE_URL=postgresql://postgres:password@localhost:5432/autobot_db
```

### 4. Database Setup & Migration

Run the migration script to create tables (`cars`, `common_issues`, `service_intervals`, `users`, `conversations`, `chat_messages`) and seed data:

```bash
python db/migrate.py
```

### 5. Launch the Application

Start the server:

```bash
python main.py
```

Open your browser at `http://localhost:7860` (if port 7860 is occupied, it automatically tries ports 7861–7869).

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
