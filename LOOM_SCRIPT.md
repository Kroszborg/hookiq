# HookIQ — Loom Demo Script
> **Target: 7–10 minutes.** This is your intern assignment submission. Walk through the live app, then explain every architectural decision and tradeoff like you're presenting to a senior engineer.

---

## SETUP BEFORE RECORDING

1. Open browser tabs:
   - **Tab 1:** `https://hookiq.kroszborg.co` (live Vercel deployment)
   - **Tab 2:** A YouTube Short you haven't analyzed yet (food/lifestyle, >500K views)
   - **Tab 3:** An Instagram Reel on a similar topic (public creator account)
2. Have the GitHub repo open: `github.com/Kroszborg/hookiq`
3. SSH into GCP VM in a visible terminal so logs are live during the demo
4. Clear any old analyses so the processing step is fresh

---

## SCRIPT

---

### [0:00 – 0:45] WHAT I BUILT AND WHY

> "Hi, I'm [Name]. For this assignment I built HookIQ — an AI tool that tells short-form video creators exactly why one video went viral and another didn't.
>
> The problem: creators post two similar videos and one gets 2 million views while the other gets 8,000. They don't know why. Current tools give you raw analytics — views, likes, follower count. None of them tell you *what in the first five seconds made someone stop scrolling*, or *which psychological patterns your top competitor is using that you're not*.
>
> HookIQ solves that. You paste two video URLs — any combination of YouTube Shorts, Instagram Reels, or TikTok — and get: full transcript extraction, engagement analysis, AI-scored hook quality, viral pattern detection, a visual content timeline, and a streaming RAG chatbot that can answer questions about both videos with citations back to the actual transcript.
>
> The entire stack is zero-cost in production. Let me show you the app first, then walk through every technical decision."

---

### [0:45 – 1:15] LIVE INPUT

> *(Show the homepage at hookiq.kroszborg.co)*
>
> "This is the live deployment — Next.js 16 on Vercel, FastAPI backend on a GCP e2-small VM. I'll paste two URLs I haven't analyzed before."

*(Paste a YouTube Short URL into field A, Instagram Reel into field B)*

> "Notice the platform detection — the dot next to each input turns red for YouTube, pink for Instagram. That's just a visual indicator so users know the system recognized the URL. Hit Analyze."

*(Click Analyze)*

---

### [1:15 – 2:30] PROCESSING — EXPLAIN THE PIPELINE WHILE IT RUNS

> *(Progress bar animating with steps)*
>
> "While this runs — which takes 30 to 90 seconds — let me walk through what's actually happening in the backend.

**Step 1: Transcript extraction.**
> For YouTube I use `youtube-transcript-api` which pulls captions directly from YouTube's subtitle API — no audio download, no transcription cost, instant. I added dual-version support with a fallback because the library had a breaking change in v1.0 that removed the class method interface. If captions aren't available, it falls back to yt-dlp audio download + faster-whisper.
>
> For Instagram, there are no captions, so I download the audio with yt-dlp and run it through faster-whisper locally — the tiny model, int8 quantized, on CPU. It runs in under 30 seconds for a 60-second reel. No Deepgram, no OpenAI Whisper API, no paid transcription service.

**Step 2: Metadata extraction.**
> yt-dlp's `--dump-json` flag returns views, likes, comments, duration, upload date, thumbnail, hashtags, and follower count in one shot for both platforms. For Instagram, follower count is sometimes missing from yt-dlp's output, so I fall back to instaloader as a secondary source. Instagram doesn't expose view counts through its CDN API — even with authenticated cookies — so the engagement rate falls back to a follower-based calculation, which is actually the standard KPI that Instagram creator tools use.

**Step 3: Chunking and embedding.**
> The transcript gets chunked into 500-token segments with 100-token overlap using tiktoken — the overlap prevents context loss at chunk boundaries. Each chunk gets embedded using BAAI/bge-small-en-v1.5, a 384-dimension sentence transformer that runs locally inside the Docker container. Vectors get upserted into Qdrant tagged with the analysis ID and video label A or B.

**Step 4: Intelligence layer.**
> Eight sequential Groq API calls using LLaMA 3.3 70B in JSON mode: hook analysis (4 scores), structure segmentation, viral pattern detection for each video, cross-video comparison, and 5 ranked improvement recommendations. All return validated Pydantic models — I have per-field validation so one bad LLM response doesn't crash the entire analysis load."

*(Analysis completes)*

---

### [2:30 – 4:00] DASHBOARD WALKTHROUGH

> *(Dashboard visible with both video cards)*

**Video cards:**
> "Each card shows the real extracted data — views, likes, comments, follower count, upload date, hashtags. The Viral Score is my composite 0-100 metric. I compute it client-side from three components: hook quality average (40% weight), viral pattern count (30%), and normalized engagement rate (30%). This formula is deliberately simple and interpretable — a creator can understand exactly why their score is 57 versus 72.

**Content Timeline:**
> *(Scroll to timeline)*
> "The content timeline visualizes the structural segments the LLM identified — Hook, Story, Value, CTA — as proportional bars with real timestamps from the transcript. Purple is Hook, blue is Story, green is Value Delivery, orange is CTA. This gives creators a visual answer to 'how long is my hook compared to my competitor's?'"

**What stopped the scroll:**
> *(Point to the hook callout)*
> "This is the actual first-five-seconds transcript — the literal words that made someone not swipe past. This is extracted from the timestamped whisper segments, not summarized. For Video A it's: [read it aloud]. That's a real curiosity gap — the word 'supposedly' and the superlative 'best in LA' create an open loop."

**Hook analysis scores:**
> "Four dimensions scored 1-10 by the LLM with the actual transcript as context: curiosity (does it create a question the viewer needs answered?), emotional resonance (does it trigger a feeling?), clarity (is the premise immediately understood?), and retention potential (does it give the viewer a reason to stay?). These map directly to what platform recommendation algorithms optimize for."

**Viral patterns:**
> "Six psychological patterns detected with transcript evidence: curiosity gap, open loop, social proof, authority, urgency, novelty. The checked ones are present with evidence, the circles are absent. For improvement recommendations I cross-reference — if Video A has social proof but Video B doesn't, recommendation 1 is specifically about adding social proof."

**Performance benchmark:**
> *(Point to the bar chart)*
> "The benchmark compares both videos' viral scores and engagement rates against the ~3.5% industry average. This is context creators actually need — 4% ER sounds okay until you see it's only marginally above average."

---

### [4:00 – 5:30] RAG CHAT — THE AI LAYER

> *(Switch to Chat tab)*
>
> "Now the part I'm most proud of — the RAG chatbot. This is built on LangGraph, Anthropic's open-source orchestration framework for stateful AI agents."

*(Type: "Why did Video A outperform Video B?")*

> *(Wait for streaming response)*
>
> "Watch how it streams — this is Server-Sent Events, not WebSockets. The backend generates tokens via Groq streaming and pushes them through an SSE endpoint. The frontend reads the stream via `EventSource`. SSE was the right call here over WebSockets because it's unidirectional — the server pushes, the client reads — and it works through any HTTP proxy including Nginx without special configuration.

**Citations:**
> "See those citation tags — [A-Chunk-0], [B-Chunk-1]. These reference actual Qdrant chunks retrieved by vector search. The RAG retrieval works like this: the user's message gets embedded with BGE-small, then I run two parallel Qdrant queries — top 5 chunks from Video A filtered by analysis_id and label='A', top 5 from Video B filtered by label='B'. Those 10 chunks get injected into the system prompt. The LLM is instructed to cite chunk tags when it uses them. Then I filter the citations in the response to only show tags that actually appear in the generated text."

*(Type a follow-up: "What specific technique should I borrow from Video A's hook?")*

> "I didn't re-explain the context. The system remembered because of LangGraph's MemorySaver checkpointer — it persists conversation state keyed by a session ID that the frontend generates on first load and passes with every chat request. Each turn replays the full message history in the LangGraph state graph before generating the next response. This is proper conversation memory, not just prepending recent messages."

*(Type: "What's the follower count for the creator in Video A?")*

> "It can answer metadata questions too. The creator name, follower count, engagement rate, platform, upload date — all of this is in the system prompt as structured context alongside the retrieved chunks. The LLM has full access to both the quantitative data and the qualitative transcript evidence."

---

### [5:30 – 7:00] ARCHITECTURE DECISIONS AND TRADEOFFS

> "Let me walk through every major technical decision and why I made it — because the choices compound."

---

**LLM: Groq LLaMA 3.3 70B over GPT-4o**
> "At 8 LLM calls per analysis: GPT-4o costs roughly $0.40–0.80 per analysis. Groq's free tier is $0. At 1,000 analyses per day that's $400–800/month versus $0. The quality difference on structured JSON extraction tasks — which is all I'm doing — is negligible. LLaMA 3.3 70B follows JSON mode reliably, fits the context window, and Groq's inference is fast enough that 8 sequential calls complete in under 10 seconds.
>
> Tradeoff: Groq has a 100K token-per-day limit on the free tier. I hit this during development. My solution: separate Groq models have separate quotas, so I added a `GROQ_MODEL` env var. When the 70B model is exhausted, I switch to `llama-3.1-8b-instant` which has a 500K TPD limit. I also wired in Gemini Flash as a full fallback via a single `LLM_PROVIDER` env var. No code change, just an environment variable."

---

**Embeddings: BGE-small-en-v1.5 over OpenAI text-embedding-3-small**
> "BGE-small runs locally — 384 dimensions, pre-downloaded into the Docker image at build time. At 1,000 analyses per day with ~10 chunks per analysis, OpenAI embeddings would cost roughly $0.13/day — small, but the latency of an API call versus an in-process numpy operation is meaningful. More importantly, BGE-small outperforms OpenAI's ada-002 on the BEIR retrieval benchmark.
>
> Tradeoff: it adds ~200MB to the Docker image and ~3 seconds to startup. Worth it."

---

**Vector DB: Qdrant self-hosted over Pinecone**
> "Pinecone's free tier is 100K vectors — that's roughly one week of production usage at scale. Qdrant runs in Docker with a persistent named volume. Zero cost, no API keys, cosine similarity search with payload filtering by analysis_id and label in a single query.
>
> Tradeoff: I manage the infrastructure. If the VM dies, Qdrant data is lost. In production I'd add a volume backup cron job. For this scale it's fine."

---

**Database: SQLite with SQLAlchemy async over PostgreSQL**
> "SQLite is zero-infrastructure — it's a file on disk. For a demo or small scale deployment, it's completely appropriate. The async driver (aiosqlite) means database calls don't block the FastAPI event loop.
>
> Tradeoff: SQLite doesn't handle concurrent writes well. At scale I'd swap `DATABASE_URL` to PostgreSQL — the SQLAlchemy models are the same, it's a one-line config change."

---

**Transcript extraction: youtube-transcript-api + faster-whisper over paid APIs**
> "YouTube captions are free and instant — no audio processing required. For Instagram, faster-whisper tiny on CPU transcribes a 60-second video in ~25 seconds on an e2-small. Deepgram would cost ~$0.006/minute — small but adds up. Word-level timestamps from faster-whisper enable the transcript viewer's color-coded segment highlighting, which a paid API may not return in the same format.
>
> Tradeoff: CPU whisper is ~3x slower than GPU. For production, I'd use an e2-medium or add a GPU instance for transcription."

---

**URL caching**
> "SHA-256 hash of the URL checked against the database before any extraction runs. If the same video was analyzed before, we skip the entire pipeline and reuse the existing transcript and Qdrant vectors. A repeated analysis is instant.
>
> This was an explicit design decision — in production, many creators will analyze the same viral video multiple times across different comparisons. The cache means the 30–90 second pipeline runs once per video, not once per analysis pair."

---

**Deployment: GCP VM + Vercel over a PaaS**
> "A GCP e2-micro is free tier forever. e2-small is $13/month. For a demo project, this is the right call. Docker Compose on a single VM keeps the architecture simple — Qdrant and the FastAPI backend run as services in the same compose file, communicate over the Docker bridge network, and share a named volume for the SQLite database.
>
> Vercel handles the Next.js frontend — CDN, SSL, CI/CD from git push — all free tier.
>
> Tradeoff: single VM is a single point of failure. No horizontal scaling. For production: Kubernetes, managed Qdrant, Cloud SQL for PostgreSQL. But for 0 to 10,000 users/day, this architecture works and costs ~$13/month."

---

### [7:00 – 7:45] WHAT I'D DO DIFFERENTLY / FUTURE IMPROVEMENTS

> "Three things I'd improve with more time:

**1. Parallel LLM calls.** The 8 intelligence calls run sequentially right now because Groq's free tier rate-limits concurrent requests. With a paid tier or a different provider, I'd run hook_a, hook_b, structure_a, structure_b as 4 parallel asyncio tasks, cutting the intelligence layer from ~8s to ~3s.

**2. Proper auth and multi-tenancy.** Right now there's no user authentication. Analysis IDs are UUIDs but anyone with the link can view. In production: Clerk or NextAuth for Google OAuth, row-level analysis ownership in the database, private vs. shareable report modes.

**3. TikTok support.** yt-dlp supports TikTok URLs, the platform detection is already in the code, and the pipeline would work the same way. I left it out because TikTok's API is more restrictive and I didn't want to demo something I couldn't guarantee would work live. The architecture is ready for it."

---

### [7:45 – 8:00] CLOSE

> "The full stack: Next.js 16 on Vercel, FastAPI + LangGraph on GCP, Qdrant + faster-whisper running locally in Docker, BGE embeddings at zero cost, Groq LLaMA 3.3 for intelligence. No paid API for transcription, no paid vector database, no paid embedding service.
>
> GitHub: github.com/Kroszborg/hookiq. Live demo: hookiq.kroszborg.co.
>
> Happy to go deeper on any part of the architecture."

---

## BACKUP Q&A — TECHNICAL INTERVIEW PREP

**"Walk me through the RAG pipeline step by step."**
> "User message → BGE-small embeds the query locally (in-process, no API call) → two parallel Qdrant `query_points()` calls with cosine similarity, filtered by `analysis_id` and `label='A'` or `label='B'`, returning top 5 chunks each → 10 chunks formatted as `[A-Chunk-0] text... [B-Chunk-2] text...` injected into the LangGraph system prompt → LangGraph's retrieve_node runs this, then passes state to generate_node → Groq LLaMA 3.3 streams the response with citation tags → frontend receives SSE chunks, accumulates text, parses final citations from a separate `citations` SSE event."

**"Why LangGraph instead of just calling the LLM directly?"**
> "LangGraph gives me the MemorySaver checkpointer — per-session conversation state that persists across HTTP requests without a database. Each chat session gets a `thread_id` (the session UUID), and LangGraph replays the full message history from the in-memory checkpoint on every turn. I also get a clean node graph — retrieve_node → generate_node — that's easy to extend. Adding a tool-use node or a query-rewriting node later is a graph edge, not a refactor."

**"How does the CORS issue you mentioned work?"**
> "FastAPI's CORSMiddleware sets `Access-Control-Allow-Origin` based on the `FRONTEND_URL` env var. When I added Nginx as an SSL proxy, I also added CORS headers in the Nginx config — both were setting the same header, the browser saw the duplicated value `https://hookiq.kroszborg.co, https://hookiq.kroszborg.co` and rejected it. Fix: remove all CORS headers from Nginx, let FastAPI own CORS entirely, Nginx just proxies."

**"Why SQLite and not PostgreSQL from the start?"**
> "SQLite is zero-infrastructure for a solo project on a single VM. The async SQLAlchemy setup is identical — the only difference is the `DATABASE_URL` connection string. I'd migrate to PostgreSQL before adding multi-tenancy or concurrent write-heavy load. It's a one-line change in `.env`."

**"What's the biggest technical risk in production?"**
> "The Groq token limit. 100K tokens per day on the free tier. Each analysis uses ~8K tokens across 8 calls, so that's ~12 analyses per day before hitting the limit. Mitigation: I've built in automatic retry with exponential backoff, a `GROQ_MODEL` env var to switch to `llama-3.1-8b-instant` (which has a separate 500K TPD quota), and a `LLM_PROVIDER=gemini` fallback. In production you'd use a paid Groq tier — $0.05 per million tokens, effectively infinite budget."

**"How does the viral score formula work and why those weights?"**
> "Three components: hook quality average (curiosity + emotional + clarity + retention, averaged) weighted 40%, viral pattern count (out of 6 patterns, normalized) weighted 30%, and normalized engagement rate weighted 30%. The 40% weight on hook reflects the research consensus that the first 3-5 seconds drive 80% of a video's reach via the platform algorithm's completion signal. The pattern and ER components are equal because they're both trailing indicators — they tell you what worked, but hook quality predicts what will work. The formula is intentionally simple and inspectable — a creator should be able to understand their score."

**"Is the transcript analysis actually accurate?"**
> "It's as accurate as the source. YouTube captions are auto-generated by Google's ASR — high quality. Faster-whisper tiny has ~5-10% WER on clean English audio. The LLM analysis on top of that is qualitative — it can be wrong. I don't claim these scores are ground truth, I claim they're a consistent, explainable framework for comparison. Two videos analyzed with the same prompts on the same model give comparable scores. That's the value — relative comparison, not absolute truth."
