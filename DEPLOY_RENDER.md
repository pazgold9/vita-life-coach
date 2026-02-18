# Deploy Vita to Render

The course requires the agent to be deployed on [Render](https://render.com). Below: backend only (required). Optionally run the Next.js frontend locally against the deployed API, or add a second Render service for the frontend.

---

## 1. Prepare the repo

- Commit and push all code to **GitHub** (no `.env` — it's in `.gitignore`).
- Do **not** put API keys in the repo. You will add them in Render's dashboard.

---

## 2. Create a Render Web Service (backend)

1. Go to [dashboard.render.com](https://dashboard.render.com) and sign in.
2. **New** → **Web Service**.
3. Connect your **GitHub** account and select the repo `vita_life_coach`.
4. Configure:
   - **Name:** e.g. `vita-life-coach`
   - **Region:** choose closest to you.
   - **Branch:** `main` (or the branch you use).
   - **Runtime:** `Python 3`.
   - **Build Command:**
     ```bash
     pip install -r backend/requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance type:** Free (or paid if you need more resources).

---

## 3. Environment variables (Render dashboard)

In the service → **Environment** tab, add these **key/value** pairs. Get the **values** from your LLMod.ai, Pinecone, and Supabase dashboards — do not paste real keys into the repo or this file.

| Key | Description | Where to get value |
|-----|-------------|--------------------|
| `LLMOD_API_KEY` | LLM API key | LLMod.ai (course provider) |
| `LLMOD_BASE_URL` | LLM API base URL | LLMod.ai (e.g. `https://api.llmod.ai/v1`) |
| `LLMOD_MODEL` | Model name | Optional; default in code |
| `LLMOD_EMBEDDING_MODEL` | Embedding model | Optional; default in code |
| `PINECONE_API_KEY` | Pinecone API key | Pinecone console |
| `PINECONE_INDEX_NAME` | Index name | Pinecone console (e.g. `vita-life-coach`) |
| `SUPABASE_URL` | Supabase project URL | Supabase → Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key | Supabase → Settings → API (service_role, not anon) |
| `GROUP_BATCH_ORDER_NUMBER` | For `/api/team_info` | Your batch/order (e.g. `batch1_1`) |
| `TEAM_NAME` | For `/api/team_info` | Your team name |
| `STUDENT_1_NAME`, `STUDENT_1_EMAIL` | For `/api/team_info` | Same for students 2 and 3 if required |

After saving, Render will redeploy. The service URL will be like:  
`https://vita-life-coach-xxxx.onrender.com`

---

## 4. Check the backend

- Open: `https://<your-service-name>.onrender.com/docs` (Swagger UI).
- Test:
  - `GET /api/team_info`
  - `GET /api/agent_info`
  - `POST /api/execute` with body `{"prompt": "What are good sources of iron?"}`

If these work, the **agent is deployed** as required by the course.

---

## 5. Frontend (optional)

**Option A – Use the app locally with deployed backend**

1. In `frontend-next`, create `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=https://<your-service-name>.onrender.com
   ```
2. Run:
   ```bash
   cd frontend-next && npm run dev
   ```
3. Use the app at `http://localhost:3000`; it will call the Render backend.

**Option B – Second Render service for Next.js**

1. **New** → **Web Service**.
2. Connect the same repo.
3. **Root Directory:** `frontend-next`.
4. **Runtime:** `Node`.
5. **Build:** `npm install && npm run build`.
6. **Start:** `npm run start`.
7. Add env: `NEXT_PUBLIC_API_URL=https://<your-backend-service>.onrender.com`.
8. After deploy, open the frontend URL; backend is used via that env var.

---

## 6. Notes

- **Free tier:** Service may sleep after inactivity; first request can be slow (cold start).
- **Budget:** LLMod.ai has a $13 budget; avoid excessive runs and large ingestions on the deployed app.
- **CORS:** Backend allows all origins (`allow_origins=["*"]`); if you restrict later, add your frontend URL.
- **Secrets:** Never commit `.env` or real keys. Use only Render (and optionally `.env.local` locally) for secrets.

---

## Submission (course)

Submit in the required format:

- **Render URL:** `https://<your-service-name>.onrender.com`
- **GitHub Repo URL:** `https://github.com/<your-org>/vita_life_coach`

Keep the Render service active until the project is graded.
