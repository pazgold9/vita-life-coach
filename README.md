# Vita — AI-Powered Wellness & Nutrition Coach

Vita is a multi-agent AI wellness coach that reduces **nutrition confusion** and **adherence friction**. It uses an **Orchestrator Agent (Head Coach)** that orchestrates three specialist agents in parallel: **Nutrition Expert** (RAG + TDEE), **Science Researcher** (live PubMed + RAG fallback), and **Wellness Coach** (RAG + reasoning).

## Live Demo

The app is deployed on Render: **https://vita-life-coach.onrender.com/**

## Architecture

- **Head Coach (Orchestrator)** — ReAct reasoning loop; routes sub-tasks to specialists in parallel; extracts user profile via regex (no extra LLM call); synthesizes the final response.
- **Nutrition Expert** — RAG over Open Food Facts + USDA; calculates TDEE using the Mifflin-St Jeor equation.
- **Science Researcher** — Live PubMed search via NCBI E-utilities API; falls back to local RAG on network error.
- **Wellness Coach** — RAG over wellness-focused PubMed abstracts; handles stress, exercise, sleep, and mindfulness.

Architecture diagram: `assets/architecture.png`

## Run locally

1. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Build the Next.js frontend:
   ```bash
   cd frontend-next && npm install && npm run build && cd ..
   ```
3. Create `.env` in the project root (see **Environment variables** below).
4. Start the app:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
5. Open http://localhost:8000

The Next.js static export is served directly by the FastAPI backend. If `frontend-next/out/` does not exist it falls back to the legacy vanilla-JS frontend in `frontend/`.

## Environment variables (`.env`)

```
# LLMod.ai — required
LLMOD_API_KEY=your_llmod_api_key_here
LLMOD_BASE_URL=https://api.llmod.ai/v1
LLMOD_MODEL=gpt-4o-mini
LLMOD_EMBEDDING_MODEL=text-embedding-3-small

# Pinecone — required for RAG
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=vita-rag

# Supabase — optional (profile + conversation history persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# Team info — optional (for /api/team_info)
# GROUP_BATCH_ORDER_NUMBER=batch1_1
# TEAM_NAME=Vita Team
# STUDENT_1_NAME=...  STUDENT_1_EMAIL=...
# STUDENT_2_NAME=...  STUDENT_2_EMAIL=...
# STUDENT_3_NAME=...  STUDENT_3_EMAIL=...
```

The agent runs without RAG (specialists use LLM only) when Pinecone is not configured. Profile and conversation history degrade gracefully to in-memory / no-op when Supabase is not configured.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/team_info` | Team and student details |
| `GET` | `/api/agent_info` | Agent description, purpose, prompt template, examples |
| `GET` | `/api/model_architecture` | Architecture diagram (PNG) |
| `POST` | `/api/execute` | Run the agent (synchronous) |
| `POST` | `/api/execute_stream` | Run the agent with SSE streaming |
| `GET` | `/api/profile` | Get current user profile |
| `PUT` | `/api/profile` | Update user profile fields |
| `POST` | `/api/profile/reset` | Clear user profile |
| `GET` | `/api/history` | Recent conversation history |
| `GET` | `/api/env_check` | Check which env vars are configured |

### POST /api/execute

**Request:**
```json
{ "prompt": "..." }
```

**Success response:**
```json
{
  "status": "ok",
  "error": null,
  "response": "...",
  "steps": [
    {
      "module": "Head Coach",
      "prompt": { "messages": [] },
      "response": { "content": "..." }
    }
  ]
}
```

**Error response:**
```json
{
  "status": "error",
  "error": "Human-readable description",
  "response": null,
  "steps": []
}
```

Each step object contains:
- `module` — agent name (matches architecture diagram: `Head Coach`, `Nutrition Expert`, `Science Researcher`, `Wellness Coach`)
- `prompt` — the exact input sent to the LLM
- `response` — the raw LLM output

### POST /api/execute_stream

Same request format as `/api/execute`. Returns a Server-Sent Events (SSE) stream with progress events (`orchestrator_start`, `orchestrator_thinking`, `specialist_start`, `specialist_done`, `composing`, `done`, `result`, `error`) followed by the same final JSON payload.

## Frontend

The primary frontend is a **Next.js** app (`frontend-next/`) with:

- **Profile gate** — collects name, age, sex, weight, height, activity level, dietary restrictions, medical conditions, and goals before the first chat turn (up to 2 skips allowed for anonymous mode).
- **Real-time activity timeline** — streams orchestrator reasoning and specialist progress via SSE.
- **Conversation history** — last 10 turns sent to the backend for context; history displayed in a collapsible side panel.
- **Suggested prompts** — pre-filled templates to get started quickly.

A minimal legacy vanilla-JS frontend (`frontend/`) remains as a fallback.

## Data ingestion (Pinecone)

Create a Pinecone index with dimension matching your embedding model (e.g. 1536 for `text-embedding-3-small`). From the project root:

- **PubMed** (namespace `pubmed`):
  ```bash
  python -m backend.data_ingestion.pubmed
  ```
- **Open Food Facts** (namespace `openfoodfacts`):
  ```bash
  python -m backend.data_ingestion.openfoodfacts
  ```
- **USDA** (namespace `usda`) — requires Kaggle credentials (`~/.kaggle/kaggle.json` or `KAGGLE_USERNAME`/`KAGGLE_KEY`):
  ```bash
  python -m backend.data_ingestion.usda
  ```
- **Wellness PubMed** (namespace `wellness`):
  ```bash
  python -m backend.data_ingestion.wellness_pubmed
  ```

Datasets used:
- PubMed: [`ccdv/pubmed-summarization`](https://huggingface.co/datasets/ccdv/pubmed-summarization) (Hugging Face)
- Open Food Facts: [`openfoodfacts/product-database`](https://huggingface.co/datasets/openfoodfacts/product-database) (Hugging Face)
- USDA: [`joebeachcapital/fooddata-central`](https://www.kaggle.com/datasets/joebeachcapital/fooddata-central) (Kaggle — `kagglehub`)

Requires `PINECONE_API_KEY` and `LLMOD_API_KEY`. USDA also requires Kaggle credentials.
