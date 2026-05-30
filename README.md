# HookIQ

**Understand why one video went viral and another didn't.**

HookIQ is a production-grade SaaS that lets creators compare YouTube Shorts and Instagram Reels using AI-powered transcript intelligence, engagement analysis, LangGraph RAG chat, and viral pattern detection.

---

## Architecture

```
User → Next.js 16 Frontend (Vercel)
             ↓ POST /analyze
       FastAPI Backend (Docker, GCP VM)
             ↓ parallel extraction
  ┌──────────────────┐    ┌──────────────────────┐
  │  YouTube Short   │    │  Instagram Reel      │
  │  ─────────────── │    │  ──────────────────  │
  │  youtube-        │    │  yt-dlp metadata     │
  │  transcript-api  │    │  instaloader         │
  │  yt-dlp metadata │    │  yt-dlp audio dl     │
  └────────┬─────────┘    │  faster-whisper tiny │
           │              └──────────┬───────────┘
           └──────────┬─────────────┘
                      ↓
          Clean → Chunk (500t / 100o)
                      ↓
        BGE-small-en-v1.5 Embeddings (384-dim)
                      ↓
        Qdrant (self-hosted Docker, persistent)
                      ↓
        Gemini 2.0 Flash (Intelligence Layer)
        ├── Hook Analysis (4 scores)
        ├── Structure Analysis (Hook/Story/Value/CTA)
        ├── Viral Patterns (6 patterns)
        ├── Comparison Insights
        └── 5 Recommendations
                      ↓
         SQLite cache (video + analysis records)
                      ↓
       POST /chat → LangGraph Agent (SSE stream)
       ├── Qdrant hybrid retrieval (top 5 × 2)
       ├── [A-Chunk-N] / [B-Chunk-N] citations
       └── MemorySaver (per session memory)
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind v4, shadcn/ui | App Router, dark mode, fast Turbopack builds |
| Backend | FastAPI + Python 3.12 | Async-native, automatic OpenAPI docs |
| Orchestration | LangGraph 0.2 | Stateful agent graph with per-session memory |
| Embeddings | BAAI/bge-small-en-v1.5 (sentence-transformers) | **Free**, 384-dim, ~50ms/batch on CPU, no API key |
| Vector DB | Qdrant (self-hosted Docker) | **Free**, persistent volumes, fast cosine search, filter by metadata |
| LLM | Gemini 2.0 Flash | **Free tier** (1M tokens/day), fast, JSON mode |
| YT Transcript | youtube-transcript-api → yt-dlp fallback | No API key, sub-second for most videos |
| IG Transcript | yt-dlp (audio) + faster-whisper tiny | **Free**, runs in container, ~30s on CPU |
| DB | SQLite (aiosqlite + SQLAlchemy) | Zero-config, no separate service |
| Deploy | Docker Compose on GCP VM + Vercel | **Free tier** for both |

---

## Cost Analysis

| Component | Cost @ 1,000 creators/day | Cost @ 10,000 creators/day |
|---|---|---|
| Gemini 2.0 Flash | $0.00 (free tier) | ~$2/day (if exceeds free tier) |
| BGE-small embeddings | $0.00 (CPU, in-container) | $0.00 |
| Qdrant self-hosted | $0.00 (Docker volume) | $0.00 (scale VM) |
| faster-whisper tiny | $0.00 (CPU, ~30s/video) | $0.00 (queue if needed) |
| GCP e2-micro VM | $0.00 (always-free tier) | ~$13/mo (e2-small upgrade) |
| Vercel frontend | $0.00 (free tier) | $0.00 |
| **Total per analysis** | **$0.00** | **~$0.001** |

**URL caching**: Same URL = zero pipeline re-run. Cost per repeat = $0.00.

---

## Scalability

### Why Qdrant over Pinecone
- Self-hosted = zero cost (Pinecone free tier: 1 index, 100K vectors)
- Qdrant supports rich payload filtering (analysis_id + label) natively
- No egress costs, no vendor lock-in
- At 10K creators/day, a $10/month VM handles Qdrant + backend together

### Why BGE over OpenAI Embeddings
- OpenAI text-embedding-3-small: $0.00002/1K tokens → ~$0.02 per analysis
- BGE-small: $0.00 (runs on CPU in 50ms)
- At 1K creators/day: saves $20/day
- Quality is comparable for retrieval tasks (MTEB leaderboard top-10)

### Why Gemini Flash over GPT-4o
- Gemini 2.0 Flash free tier: 1M tokens/day — covers ~500+ analyses/day at zero cost
- GPT-4o: ~$0.005/1K tokens input → $0.50+ per analysis
- At 1K creators/day: saves $500/day

### Scaling to 1,000 creators/day
- Single GCP e2-micro (1 vCPU, 1GB RAM) handles ~20 concurrent analyses
- BGE model loaded once at startup (singleton)
- Whisper model loaded once at startup (singleton)
- SQLite handles 1K writes/day without issue
- URL caching means repeat URLs (common for popular videos) cost nothing

### Scaling to 10,000 creators/day
- Upgrade to e2-standard-2 (2 vCPU, 8GB RAM) → ~$50/month
- Add Redis queue (Celery) for background pipeline jobs
- Separate Qdrant to its own container with more storage
- SQLite → PostgreSQL (async) for concurrent writes
- Frontend stays on Vercel free tier (static + SSR)

---

## Setup

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12 (for local dev only)
- Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Local Development

**1. Clone and configure**
```bash
git clone <repo>
cd hookiq
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY
```

**2. Start backend + Qdrant**
```bash
docker-compose up --build
```
Backend: http://localhost:8000  
API docs: http://localhost:8000/docs  
Qdrant dashboard: http://localhost:6333/dashboard

**3. Start frontend**
```bash
cd frontend
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```
Frontend: http://localhost:3000

### GCP VM Deployment

**1. Create VM**
```bash
# Free tier: e2-micro in us-central1, us-west1, or us-east1
gcloud compute instances create hookiq-vm \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=http-server,https-server
```

**2. Open port 8000**
```bash
gcloud compute firewall-rules create allow-hookiq \
  --allow=tcp:8000 \
  --target-tags=http-server
```

**3. Install Docker on VM**
```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

**4. Deploy**
```bash
git clone <repo> && cd hookiq
echo "GEMINI_API_KEY=your_key_here" > .env
echo "FRONTEND_URL=https://your-app.vercel.app" >> .env
docker compose up -d --build
```

**5. Deploy frontend to Vercel**
```bash
cd frontend
vercel --prod
# Set NEXT_PUBLIC_API_URL=http://<VM_EXTERNAL_IP>:8000 in Vercel env vars
```

---

## Environment Variables

### Backend (`.env` at project root for Docker Compose)
| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Google AI Studio key |
| `QDRANT_COLLECTION` | `video_chunks` | Qdrant collection name |
| `FRONTEND_URL` | `http://localhost:3000` | CORS origin for frontend |
| `WHISPER_MODEL` | `tiny` | Whisper model size (tiny/base/small) |
| `WHISPER_DEVICE` | `cpu` | cpu or cuda |
| `WHISPER_COMPUTE_TYPE` | `int8` | int8 for CPU efficiency |

### Frontend (`.env.local`)
| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Start analysis, returns `{analysis_id}` immediately |
| `GET` | `/analyze/progress/{id}` | SSE stream of pipeline progress events |
| `GET` | `/analyze/{id}` | Full analysis result (videos + insights) |
| `POST` | `/chat` | SSE streaming RAG chat with memory |
| `GET` | `/history` | List of past analyses |
| `GET` | `/health` | Health check |

---

## Tradeoffs

| Decision | Tradeoff |
|---|---|
| SQLite over PostgreSQL | Zero-config but single-writer; swap to async PostgreSQL for >100 concurrent users |
| Whisper tiny over base | ~30s vs ~60s, slight accuracy loss for short clips — acceptable for demo |
| In-process Qdrant over cluster | No network overhead, but vertical scale only |
| BGE-small over BGE-large | 5x faster, slightly lower recall — fine for 500-token chunks |
| MemorySaver over persistent store | Memory-only; restart clears chat history — use SqliteSaver for persistence |

---

## Future Improvements

- [ ] Persistent LangGraph checkpointer (SqliteSaver) so chat memory survives restarts
- [ ] Celery + Redis for async job queue (scale beyond single-process)
- [ ] Whisper base/small for higher accuracy on long-form content
- [ ] TikTok support via yt-dlp
- [ ] User authentication + per-user analysis history
- [ ] Batch analysis (compare 5+ videos at once)
- [ ] Export report as PDF
- [ ] Webhook notifications when analysis completes
