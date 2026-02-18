# Vita — AI-Powered Wellness & Nutrition Coach

Vita is an AI agent that reduces **nutrition confusion** and **adherence friction** using an Orchestrator Agent (Head Coach) and three specialists: **Nutrition Expert** (RAG), **Science Researcher** (RAG), and **Wellness Coach**.

## Where to set `LLMOD_API_KEY`

- **Locally:** Create a file named `.env` in the project root (`vita_life_coach/`) and add:
  ```bash
  LLMOD_API_KEY=your_key_here
  LLMOD_BASE_URL=https://...   # from LLMod.ai platform
  ```
  Copy from `.env.example`: `cp .env.example .env` then edit `.env`. The app loads `.env` automatically. **Do not commit `.env`** (it is in `.gitignore`).
- **On Render:** In the Render dashboard → your service → **Environment** → add `LLMOD_API_KEY` and `LLMOD_BASE_URL` (and other keys). Render injects these at runtime.

Get your API key and base URL from the **LLMod.ai** platform (one key per group; all members share it).

## Budget ($13)

LLMod.ai gives you **$13 total**. To stay within budget:

- **Agent runs:** Each Run Agent call does several LLM calls (plan + specialists + synthesize). Use **short prompts** and **fewer test runs**.
- **Models:** We use `gpt-4o-mini` by default (cheaper). You can set `LLMOD_MODEL` in `.env` to a smaller/faster model if the platform offers one.
- **Ingestion:** Embedding for PubMed/Open Food Facts/USDA uses the same LLMod.ai budget. Run ingestion **once** (or a few times), not on every deploy. Keep ingestion sample sizes modest (e.g. 500–2000 rows per dataset).
- **RAG:** We already use `top_k=3` and one embedding per nutrition query to reduce cost.

## Deploy on Render

See **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** for step-by-step instructions. Use **Environment** in the Render dashboard for all API keys; never commit `.env`.

## Run locally

1. From the project root:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Create `.env` and set at least `LLMOD_API_KEY` and `LLMOD_BASE_URL` (and `PINECONE_*` if using RAG).
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

## What you need to run it (checklist)

1. **`.env`** in project root with at least:
   - `LLMOD_API_KEY` and `LLMOD_BASE_URL` (from [LLMod.ai](https://llmod.ai) platform).
2. **To run the app only:** That’s enough. Start with `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` and open http://localhost:8000. The agent will run without RAG (specialists use LLM only until you ingest data).
3. **To use RAG (Nutrition + Science):**
   - **Pinecone:** Create an index (dimension = your embedding size, e.g. 1536 for `text-embedding-3-small`). Set `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` in `.env`.
   - **Ingestion:** Run the three ingestion scripts once (see below). They use:
     - **PubMed:** `load_dataset("ccdv/pubmed-summarization", "section")` — [Hugging Face](https://huggingface.co/datasets/ccdv/pubmed-summarization).
     - **Open Food Facts:** `load_dataset("openfoodfacts/product-database")` — [Hugging Face](https://huggingface.co/datasets/openfoodfacts/product-database).
     - **USDA:** `kagglehub.dataset_download("joebeachcapital/fooddata-central")` — [Kaggle](https://www.kaggle.com/datasets/joebeachcapital/fooddata-central). Requires Kaggle API (e.g. `~/.kaggle/kaggle.json` or `KAGGLE_USERNAME` / `KAGGLE_KEY`).

No extra “links” are required in code; the scripts use these loaders directly.

## Data ingestion (Pinecone)

Create a Pinecone index with dimension matching your embedding model (e.g. 1536 for `text-embedding-3-small`). From project root:

- **PubMed** (namespace `pubmed`): `load_dataset("ccdv/pubmed-summarization", "section")`
  ```bash
  python -m backend.data_ingestion.pubmed
  ```
- **Open Food Facts** (namespace `openfoodfacts`): `load_dataset("openfoodfacts/product-database")`
  ```bash
  python -m backend.data_ingestion.openfoodfacts
  ```
- **USDA** (namespace `usda`): `kagglehub.dataset_download("joebeachcapital/fooddata-central")` — install `kagglehub`, set Kaggle API credentials, then:
  ```bash
  python -m backend.data_ingestion.usda
  ```

Requires `PINECONE_API_KEY` and `LLMOD_API_KEY`. For USDA, Kaggle credentials are required.

## Architecture

- **Orchestrator Agent (Head Coach)** — Plans user goals, routes sub-tasks to specialists, synthesizes the final response.  
- **Nutrition Expert** — RAG over Open Food Facts + USDA.  
- **Science Researcher** — RAG over PubMed.  
- **Wellness Coach** — LLM-only (stress, exercise, mindfulness).

A clearer diagram is in `assets/architecture.svg`; you can export it to PNG and replace `assets/architecture.png` if needed.
