# Vita — AI-Powered Wellness & Nutrition Coach

Vita is an AI agent that reduces **nutrition confusion** and **adherence friction** using an Orchestrator Agent (Head Coach) and three specialists: **Nutrition Expert** (RAG), **Science Researcher** (RAG), and **Wellness Coach**.

## Run locally

1. From the project root:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Set environment variables (or use a `.env` file):
   - `LLMOD_API_KEY`, `LLMOD_BASE_URL` (LLM provider)
   - `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (vector DB)
3. Start the app:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Open http://localhost:8000 — use the textarea and **Run Agent** to try the agent. Response and execution steps are shown below.

## API endpoints

- `GET /api/team_info` — team/student details  
- `GET /api/agent_info` — agent description, purpose, prompt template, examples  
- `GET /api/model_architecture` — architecture diagram (PNG)  
- `POST /api/execute` — run the agent; body `{"prompt": "..."}`; returns `response` and `steps`

## Data ingestion (Pinecone)

Create a Pinecone index with dimension matching your embedding model (e.g. 1536 for `text-embedding-3-small`). Then run from project root:

- **PubMed** (namespace `pubmed`):
  ```bash
  python -m backend.data_ingestion.pubmed
  ```
- **Open Food Facts** (namespace `openfoodfacts`):
  ```bash
  python -m backend.data_ingestion.openfoodfacts
  ```
- **USDA** (namespace `usda`): download [FoodData Central](https://www.kaggle.com/datasets/joebeachcapital/fooddata-central), place the main food CSV as `data/fooddata-central.csv`, then:
  ```bash
  python -m backend.data_ingestion.usda
  ```

Requires `PINECONE_API_KEY` and `LLMOD_API_KEY`.

## Architecture

- **Orchestrator Agent (Head Coach)** — Plans user goals, routes sub-tasks to specialists, synthesizes the final response.  
- **Nutrition Expert** — RAG over Open Food Facts + USDA.  
- **Science Researcher** — RAG over PubMed.  
- **Wellness Coach** — LLM-only (stress, exercise, mindfulness).

A clearer diagram is in `assets/architecture.svg`; you can export it to PNG and replace `assets/architecture.png` if needed.
