# DarGlobal Intelligence — 100% Free Public Deployment Guide

This guide provides end-to-end instructions for deploying **DarGlobal Intelligence** publicly with zero hosting fees ($0.00 / month forever) and no credit card required.

---

## 1. Free Architecture Overview

```
                          ┌────────────────────────────────┐
                          │         Vercel (Hobby)         │
                          │   Next.js 14 Web Application   │
                          │      $0/mo (Free Forever)      │
                          └───────────────┬────────────────┘
                                          │
                  Direct Browser-to-Render HTTPS & SSE (Cross-Origin)
                                          │
                                          ▼
                          ┌────────────────────────────────┐
                          │    Render (Free Web Service)   │
                          │     FastAPI Agent & RAG API    │
                          │      $0/mo (512MB RAM Cap)     │
                          │                                │
                          │ ┌────────────────────────────┐ │
                          │ │ Ephemeral Bootstrapper     │ │
                          │ │ (Restores ChromaDB + BM25  │ │
                          │ │  from canonical_dataset)   │ │
                          │ └────────────────────────────┘ │
                          └───────────────┬────────────────┘
                                          │
                                          ▼
                          ┌────────────────────────────────┐
                          │    OpenRouter (Free Models)    │
                          │    google/gemma-4-31b-it:free  │
                          │       $0/mo (Free Tier)        │
                          └────────────────────────────────┘
```

| Component | Platform / Service | Plan | Monthly Cost | Disk / Persistence Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | [Vercel](https://vercel.com) | Hobby | **$0.00** | Serverless Edge CDN, zero idle sleep |
| **Backend** | [Render](https://render.com) | Free Web Service | **$0.00** | Ephemeral RAM filesystem; bootstraps ChromaDB & BM25 in <1s from committed `canonical_dataset.json` |
| **LLM Inference** | [OpenRouter](https://openrouter.ai) | Free Tier | **$0.00** | Free API tier (`google/gemma-4-31b-it:free` or auto-fallback) |
| **Source Control** | [GitHub](https://github.com) | Free Public/Private | **$0.00** | Automatic deployment hooks for Vercel & Render |

---

## 2. Zero-Paid-Disk Ephemeral Vector Database Strategy

### The Problem on Render Free Tier
Render Free Web Services feature **ephemeral filesystems**: any files written to local disk (such as ChromaDB sqlite files or pickled indexes) are wiped whenever the container spins down after 15 minutes of idle time or redeploys. Paid persistent disks on Render cost $1/GB/month.

### The Solution: Deterministic Canonical Ingestion
DarGlobal Intelligence solves this without paying for storage:
1. **Serialized Canonical Dataset**: All 16 canonical records (14 luxury property dossiers + 2 XML sitemaps) and 32 semantic chunks with 100% provenance fidelity are committed in [`backend/data/canonical_dataset.json`](file:///c:/PHOTOS/Personal/Projects/DarGlobal/backend/data/canonical_dataset.json).
2. **Sub-Second Cold Start Bootstrap**: On startup, `backend.app.ingestion.pipeline.IngestionPipeline(probe_live=False)` checks if ChromaDB is populated. If empty (fresh boot or after spin-down), it deterministically upserts the 32 chunks into ChromaDB and compiles the BM25 index in **< 1.0 second**.
3. **RAM Footprint Optimization**: PyTorch and heavy transformer dependencies were removed, reducing runtime memory consumption from ~450 MB down to **~121 MB RAM** (only 24% of Render's 512 MB free RAM ceiling).

---

## 3. Pre-Deployment Step: Push to GitHub

Ensure your local changes and the canonical dataset are committed and pushed to your GitHub repository:

```bash
# 1. Inspect status
git status

# 2. Stage all changes (including canonical dataset and deployment blueprints)
git add .

# 3. Commit changes
git commit -m "feat: configure 100% free deployment for Vercel and Render"

# 4. Push to your GitHub repository
git push origin master  # or 'main' depending on your default branch
```

---

## 4. Deploying the Backend on Render (Free Web Service)

### Option A: One-Click Blueprint Deployment (Recommended)
Because [`render.yaml`](file:///c:/PHOTOS/Personal/Projects/DarGlobal/render.yaml) is included in the root of the repository:
1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** > **Blueprint**.
3. Connect your GitHub repository.
4. Render will detect `render.yaml` and configure the `darglobal-backend` service automatically.
5. In the environment variable prompt, enter your `OPENROUTER_API_KEY`.
6. Click **Apply**.

---

### Option B: Manual Web Service Setup
If creating the service manually:
1. In Render Dashboard, click **New +** > **Web Service**.
2. Select **Build and deploy from a Git repository** and connect your repo.
3. Configure settings:
   - **Name**: `darglobal-intelligence-backend`
   - **Region**: Choose the closest region (e.g., Frankfurt or Oregon).
   - **Branch**: `master` (or `main`)
   - **Root Directory**: Leave blank (repository root).
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Instance Type**: **Free** (0.5 CPU, 512 MB RAM)
4. Under **Advanced**:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`
5. Under **Environment Variables**, add:

| Key | Recommended Value | Notes |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Optimal for ChromaDB and pydantic-settings |
| `ENVIRONMENT` | `production` | Enables production security controls |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Your private OpenRouter API key |
| `OPENROUTER_MODEL` | `google/gemma-4-31b-it:free` | Free model tier |
| `INGESTION_ON_STARTUP` | `true` | Restores ChromaDB & BM25 on ephemeral cold starts |
| `ADMIN_API_KEY` | *(generate a random string)* | Protects manual re-indexing endpoints |
| `CORS_ORIGIN_REGEX` | `^https:\/\/.*\.vercel\.app$` | Automatically permits all Vercel previews & production |

6. Click **Create Web Service**.
7. Once deployed, copy your Render service URL:  
   `https://<your-render-subdomain>.onrender.com`

---

## 5. Deploying the Frontend on Vercel (Hobby Tier)

1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Import your GitHub repository.
4. In the project configuration screen:
   - **Project Name**: `darglobal-intelligence`
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click **Edit** and select **`frontend`** (Important!).
   - **Build and Output Settings**: Leave defaults (`npm run build`).
5. In the **Environment Variables** section, add:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://<your-render-subdomain>.onrender.com` | Your live Render backend HTTPS URL (no trailing slash) |

6. Click **Deploy**.
7. In ~60 seconds, Vercel will assign your free production domain:  
   `https://<your-app-name>.vercel.app`

---

## 6. Verification & End-to-End Testing

Once both services are deployed, perform the following verification:

### 1. Test Backend Root & API Health
```bash
curl -i https://<your-render-subdomain>.onrender.com/health
```
**Expected Response:**
```json
HTTP/2 200
{"status":"healthy","service":"darglobal-intelligence-backend","environment":"production"}
```

```bash
curl -i https://<your-render-subdomain>.onrender.com/api/v1/health
```
**Expected Response:**
```json
HTTP/2 200
{"status":"healthy","vector_store_chunks":32,"bm25_documents":32,"openrouter_status":"connected"}
```

### 2. Verify CORS & Property Catalog
```bash
curl -i https://<your-render-subdomain>.onrender.com/api/v1/properties
```
**Expected Response:**  
Returns 14 verified luxury properties (4 Dubai, 2 Oman, 1 Qatar, 1 Spain, 6 Riyadh) with full provenance metadata (`PUBLICLY_VERIFIED_FALLBACK`).

### 3. Verify Frontend Browser Experience
1. Navigate to `https://<your-app-name>.vercel.app`.
2. Check the header status: should display a green glowing indicator with **"Live System Connected"**.
3. **Test 1: Conversational Greeting**
   - Query: `"Hello!"`
   - Result: Agent greets naturally without invoking search tools.
4. **Test 2: DarGlobal Project Search**
   - Query: `"What luxury developments does DarGlobal offer in Dubai?"`
   - Result: Agent invokes `search_darglobal_projects`, streams response, renders property cards (e.g. DaVinci Tower by Pagani, Urban Oasis by Missoni) with verified fallback badges and direct links to `darglobal.co.uk`.
5. **Test 3: Multi-Turn Contextual Filtering**
   - Query: `"Under 2000000"`
   - Result: Agent maintains Dubai + DarGlobal context, filters for projects under AED 2,000,000 (identifies Urban Oasis by Missoni at AED 1,250,000), and does not fall back to Wasalt or Riyadh.
6. **Test 4: Negative Search & Hallucination Prevention**
   - Query: `"What properties does DarGlobal offer in Tokyo?"`
   - Result: Transparent refusal stating no Tokyo properties are present in the indexed dataset, without falsely asserting DarGlobal does not operate there.

---

## 7. Render Free Tier Behavior & Best Practices

- **Cold Starts (Spin Down)**: Render Free Web Services spin down after 15 minutes of inactivity. The first request after idling may take **30 to 50 seconds** while the container boots.
- **Frontend Graceful Handling**: The Next.js frontend has built-in retry and loading states that wait for the Render container to wake up.
- **Zero Disk Decay**: Even if the container sleeps and restarts hundreds of times, the startup script will re-verify the 32 chunks from `canonical_dataset.json` in <1 second every single time.
- **Zero Cost Guarantee**: Because no paid add-ons, disks, or commercial model tiers are required, this deployment incurs **$0.00** charges indefinitely.
