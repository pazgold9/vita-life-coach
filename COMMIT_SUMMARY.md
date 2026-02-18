# Summary of changes (for Git push)

Use this as reference for commit messages or PR description. **No secrets or API keys.**

---

## Architecture & agents

- **Supervisor (Orchestrator)** + 3 **autonomous specialists** (ReAct loops).
- **Nutrition Expert**: RAG (Open Food Facts + USDA), tool `calculate_tdee`, domain boundaries.
- **Science Researcher**: RAG + **live PubMed** (`search_pubmed_live` with fallback to static RAG), PMIDs in answers.
- **Wellness Coach**: RAG (wellness PubMed namespace), `search_wellness`, domain boundaries.
- Specialists use **MAX_ITERATIONS = 2**: can decide after first search to finish or search again (autonomous, still fast when one round is enough).
- **Parallel specialist calls**: Orchestrator can call multiple specialists in one turn; no duplicate calls.
- **Supervisor verification**: Orchestrator checks specialist outputs (relevance, contradictions) before finishing.
- **Routing**: Only call specialists that fit the question; can add another specialist in a later turn if needed.
- **Off-topic / missing info**: Orchestrator can finish with a friendly message (scope, or ask for details) without calling specialists.

---

## API & backend

- **POST /api/execute** and **POST /api/execute_stream** accept `conversation_history` for multi-turn.
- **GET /api/profile** returns current user profile from Supabase.
- **Content policy errors** (e.g. Azure filter): caught and returned as a short user-friendly message instead of raw error.
- **Runner** passes `conversation_history` and optional `on_progress` to the orchestrator.
- **Profile**: Stored in Supabase `user_profiles`; extracted from conversation (age, weight, height, activity, goals, etc.); injected into orchestrator context.
- **DB**: Supabase for `conversations` and `user_profiles`; Pinecone for RAG (nutrition, research, wellness namespaces).

---

## Frontend (Next.js, Shadcn, dark mode)

- **Chat UI**: Messages array, multi-turn, history sent with each request.
- **Streaming**: SSE with live activity timeline (orchestrator thought, specialist task, specialist done + summary).
- **Prompt templates** in sidebar (generic placeholders).
- **No “conversation history” panel**: Single-session flow; profile shown in sidebar when present.
- **Dark mode**: `className="dark"` on `<html>`; muted text near-white.
- **Tip** line removed from welcome area.

---

## Data & RAG

- **Wellness RAG**: Ingestion script `wellness_pubmed.py` (NCBI E-utilities), namespace `wellness`.
- **Supabase**: Tables `conversations` and `user_profiles` (see README or DEPLOY for SQL).

---

## Files to ensure are NOT committed

- `.env` (must be in `.gitignore`) — contains `LLMOD_API_KEY`, `PINECONE_*`, `SUPABASE_*`, etc.
- Any file with real API keys or secrets.

---

## Suggested commit message (short)

```
feat: autonomous specialists (2 iter), RAG+live PubMed, profile, streaming, guardrails

- Orchestrator: routing, verification, off-topic/missing-info handling
- Specialists: MAX_ITERATIONS=2, decide finish vs search again
- Nutrition: calculate_tdee; Science: search_pubmed_live + fallback
- Supabase: user_profiles + conversations; profile extraction from chat
- Frontend: dark mode, prompt templates, SSE activity timeline
- Graceful content-policy error message
```
