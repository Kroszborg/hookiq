# HookIQ — Technical Explanation

This document explains every architectural decision in HookIQ so you can answer any interview question confidently.

---

## What the app does

HookIQ takes two social media video URLs (YouTube Shorts or Instagram Reels — any combination) and:

1. Extracts their transcripts and metadata (views, likes, comments, followers, duration, hashtags, upload date)
2. Computes engagement rate: `(likes + comments) / views × 100`
3. Chunks and embeds the transcripts, stores them in Qdrant with video labels (A or B)
4. Runs an intelligence layer: hook analysis, content structure, viral pattern detection, recommendations
5. Provides a streaming RAG chat where creators can ask why one video outperformed another — with source citations and conversation memory

---

## How RAG works in this project

**RAG = Retrieval-Augmented Generation**

Standard LLM: You ask "why did Video A do better?" — the LLM has no context about these specific videos. It just makes something up.

RAG fixes this by:
1. **Retrieving** actual transcript chunks from the vector database that are relevant to the user's question
2. **Augmenting** the LLM prompt with that retrieved context
3. **Generating** a grounded answer that references actual content from the videos

### The flow:

```
User question → BGE embed → Qdrant semantic search
                              ↓
               Top 5 chunks from Video A + Top 5 from Video B
                              ↓
               System prompt + metadata + retrieved chunks
                              ↓
               Gemini 2.0 Flash (streaming)
                              ↓
               Response with [A-Chunk-3] / [B-Chunk-7] citations
```

The critical detail: every chunk in Qdrant is tagged with `analysis_id` AND `label` (A or B). So when we retrieve, we filter by the current analysis and get context from both videos.

---

## Why LangGraph instead of LangChain

**LangGraph** is a state machine graph for AI agents. We use it for:

1. **Stateful graph**: `retrieve_node → generate_node → END` — each step has typed state
2. **MemorySaver**: Built-in checkpointing. Each chat session gets a `thread_id`. LangGraph replays the conversation state on every turn, so the model knows "Video A" from a previous message without re-explaining.

Without LangGraph memory, the second question "What about the hook?" would have no context — the model wouldn't know which videos we were discussing.

### How memory works:

```python
checkpointer = MemorySaver()
graph = graph.compile(checkpointer=checkpointer)

# Every chat turn uses the same thread_id = session_id
config = {"configurable": {"thread_id": session_id}}
result = await graph.ainvoke(input_state, config=config)
```

LangGraph replays all previous messages for that thread, so follow-up questions work naturally.

---

## Why these specific embeddings (BGE-small-en-v1.5)

**BAAI/bge-small-en-v1.5** generates 384-dimensional vectors.

| Option | Cost | Speed | Quality |
|---|---|---|---|
| OpenAI text-embedding-3-small | $0.00002/1K tokens | Fast (API) | High |
| BGE-small-en-v1.5 | $0.00 | ~50ms/batch (CPU) | High |
| BGE-large-en-v1.5 | $0.00 | ~200ms/batch (CPU) | Higher |

BGE is on the MTEB embedding leaderboard, outperforming many commercial options. For 500-token chunks of video transcripts, the quality difference vs OpenAI is negligible, and the cost saving is 100%.

At 1,000 analyses/day with ~20 chunks each = 20,000 embeddings/day:
- OpenAI cost: ~$0.04/day
- BGE cost: $0.00/day

---

## Why Qdrant

Qdrant is a purpose-built vector database written in Rust.

**Compared to alternatives:**

| Feature | Qdrant | Pinecone | ChromaDB | pgvector |
|---|---|---|---|---|
| Self-hosted | ✅ Free | ❌ SaaS only | ✅ | ✅ |
| Payload filtering | ✅ Native | ✅ | ✅ | SQL WHERE |
| Cost (self-hosted) | $0 | $70+/month | $0 | Postgres cost |
| Performance | High (Rust) | High | Medium | Medium |

The key feature we use: **payload filtering**. Every chunk in Qdrant has:
```json
{
  "analysis_id": "abc-123",
  "label": "A",
  "content": "...",
  "chunk_id": 3
}
```

When retrieving context for a chat turn, we filter by `analysis_id = current_analysis AND label = A` to get Video A chunks, and separately for label = B. This prevents contamination between different users' analyses.

---

## Why Gemini 2.0 Flash

| Model | Cost | Speed | Quality | Free Tier |
|---|---|---|---|---|
| GPT-4o | $5/1M in, $15/1M out | Fast | Best | No |
| Claude Sonnet | $3/1M in, $15/1M out | Fast | Excellent | No |
| Gemini 2.0 Flash | $0.075/1M in | Very Fast | Very Good | 1M tokens/day |
| Gemini 2.5 Flash | $0.15/1M in | Fast | Better | Limited |

At 1,000 analyses/day, the free tier covers all costs. The Flash model is specifically designed for high-throughput low-latency inference — perfect for streaming chat.

---

## Chunking strategy — why 500 tokens / 100 overlap

**Why chunk at all?** Embedding models have a context limit (~512 tokens for BGE). A 60-second reel transcript might be 200 tokens — fits in one chunk. A 10-minute video might be 2,000 tokens — needs splitting.

**Why 500 tokens?** 
- Fits within BGE's context window (512 tokens max)
- Large enough to capture a coherent thought
- Small enough for precise retrieval

**Why 100-token overlap?**
- Prevents losing context at chunk boundaries
- If a key sentence spans the split point, it appears in both chunks
- Ensures RAG can always find the relevant passage

**Chunking implementation**: We use `tiktoken` with the `cl100k_base` encoding (same as GPT-4). This counts tokens accurately instead of splitting by word count.

---

## How transcript extraction works

### YouTube

1. **Primary**: `youtube-transcript-api` — fetches captions directly from YouTube's caption API. Sub-second. No API key.
2. **Fallback**: `yt-dlp` downloads audio → `faster-whisper` (tiny model) transcribes it

### Instagram

1. **Metadata**: `yt-dlp --dump-json` extracts views, likes, comments, uploader, upload date, hashtags, thumbnail, duration
2. **Follower count**: `instaloader` fetches the creator's profile page
3. **Transcript**: `yt-dlp` downloads the reel audio → `faster-whisper` transcribes it

### faster-whisper vs openai-whisper

`faster-whisper` is a reimplementation of Whisper using CTranslate2, which is 4x faster on CPU with the same output quality. With `compute_type=int8` and the `tiny` model, transcription takes ~30 seconds on a single CPU core for a 60-second video.

---

## Engagement rate

```
engagement_rate = (likes + comments) / views × 100
```

This is the standard social media KPI. It normalizes performance across videos with different view counts. A video with 100K views and 5K interactions has a 5% engagement rate, which is strong. A video with 10M views and 50K interactions also has 0.5%, which is weak relative to its reach.

This is why comparing raw likes isn't useful — engagement rate reveals how compelling the content actually was to its audience.

---

## Caching

Every video URL is hashed (`SHA-256`) and stored in the `videos` table. Before processing any video:

```python
url_hash = hashlib.sha256(url.strip().encode()).hexdigest()
existing = await db.execute(select(Video).where(Video.url_hash == url_hash))
if existing:
    return existing  # skip all extraction, chunking, embedding
```

If the same YouTube Short is analyzed twice (by different users, or in different comparisons), we:
1. Return the cached `Video` record instantly
2. Reuse the stored transcript
3. Re-embed into Qdrant tagged with the new `analysis_id`

This means repeat URLs cost zero compute — just a database lookup and a new Qdrant tag.

---

## Streaming — how SSE works

**Server-Sent Events (SSE)** is a one-way stream from server to client over HTTP. No WebSocket handshake needed.

### Progress tracking SSE

When `POST /analyze` is called, we:
1. Create an `asyncio.Queue` keyed by `analysis_id`
2. Start a background task that processes the pipeline
3. The pipeline emits progress events to the queue at each step
4. `GET /analyze/progress/{id}` consumes the queue and yields `data: {...}\n\n` events

```python
# FastAPI endpoint
async def event_generator():
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=30.0)
        yield f"data: {json.dumps(event)}\n\n"
        if event.get("done"):
            break
```

### Chat streaming SSE

LangGraph's `astream()` yields state updates. We stream Gemini responses token-by-token:

```python
async for chunk in stream_text(system_prompt, messages):
    yield f"data: {json.dumps({'text': chunk, 'done': False})}\n\n"
```

The frontend reads this with `response.body.getReader()` and accumulates chunks in state, updating the UI on each chunk.

---

## Intelligence layer

After embedding, we call Gemini 4 more times in parallel (`asyncio.gather`):

1. **Hook analysis**: Analyzes the first 5 seconds of transcript. Scores curiosity, emotional impact, clarity, and retention potential (1-10 each). Tells you why some hooks stop scrollers.

2. **Structure analysis**: Identifies the Hook, Story, Value, CTA segments with timestamps. Visualized as the timeline bar in the UI.

3. **Viral pattern analysis**: Detects 6 patterns: Curiosity Gap, Open Loop, Social Proof, Authority, Urgency, Novelty. Each gets a present/absent flag, a score, and evidence from the transcript.

4. **Comparison + Recommendations**: Determines which video won (by engagement rate), explains why, and generates 5 specific improvements for Video B referencing actual techniques from Video A.

All 8 analysis calls (4 per video for some, 2 shared comparisons) run concurrently. Total time: ~5-8 seconds.

---

## Database schema

```sql
-- Videos table (cached, never duplicated)
videos: id, platform, url, url_hash (UNIQUE), creator, followers,
        views, likes, comments, engagement_rate, duration,
        upload_date, hashtags (JSON), transcript, thumbnail_url,
        title, created_at

-- Analyses (one per user comparison request)
analyses: id, video_a_id (FK), video_b_id (FK), status,
          hook_analysis_a (JSON), hook_analysis_b (JSON),
          structure_a (JSON), structure_b (JSON),
          viral_patterns_a (JSON), viral_patterns_b (JSON),
          recommendations (JSON), comparison_insights (JSON),
          error_message, created_at

-- Chat sessions (one per browser tab / conversation)
chat_sessions: id, analysis_id (FK), created_at

-- Messages (full history for every turn)
messages: id, session_id (FK), role, content, citations (JSON), created_at
```

Why SQLite (not PostgreSQL)?
- Zero setup, single file, zero cost
- SQLAlchemy async (`aiosqlite`) means no blocking I/O
- At 1K creators/day, SQLite handles ~10K writes/day without issue
- Swap to PostgreSQL at 100+ concurrent users by changing `DATABASE_URL`

---

## Why self-hosted Qdrant beats Pinecone at this scale

Pinecone free tier: 1 index, 100K vectors, serverless only.

1,000 creators/day × 20 chunks/video × 2 videos = 40,000 vectors/day.
After 2-3 days you hit the Pinecone limit.

Self-hosted Qdrant on a GCP e2-micro:
- 10GB disk → millions of vectors
- No request limits
- No API costs
- Docker restart policy keeps it always running

At 10K creators/day we'd upgrade to e2-small ($13/month) and give Qdrant 20GB. Still cheaper than Pinecone's paid tier at $70+/month.

---

## Scaling from 1K to 10K creators/day

**Current architecture (1K/day):**
- Single FastAPI process (uvicorn, 1 worker)
- SQLite database
- Qdrant in Docker on same VM
- BGE + Whisper models loaded once in process memory

**Bottleneck at 1K/day:**
- Whisper transcription: ~30s per Instagram Reel
- Intel single-core: can handle ~3 concurrent analyses
- Already fine for 1K/day (3 concurrent × 86400s/day ÷ 60s/analysis = ~4,320 analyses/day capacity)

**To scale to 10K/day:**
1. Add Celery + Redis as a task queue — pipelines run as background workers
2. Spawn 3-4 worker processes — each loads BGE + Whisper once at startup
3. Upgrade VM to e2-standard-4 (4 vCPU) — ~$50/month
4. Switch SQLite → PostgreSQL (async, connection pooling)
5. Qdrant on separate Docker volume with more IOPS

The chat API is already horizontally scalable since LangGraph MemorySaver is in-process. For production, swap to `SqliteSaver` or `PostgresSaver` to persist chat history across restarts.

---

## Frontend architecture

**Next.js 16** (app directory) — important differences from Next.js 15:
- `params` in dynamic routes is now a `Promise` — must `await props.params` in server components or `use(params)` in client components
- Turbopack is default for `next build`

**Component split:**
- Server components: layout, report page (static, cacheable)
- Client components: hero form, analysis page, all chat/interactive parts

**No state management library** — React's `useState` + custom hooks is sufficient. TanStack Query handles server state for history fetching.

**SSE in the browser:**
```typescript
// Progress: EventSource API
const es = new EventSource(`${API_URL}/analyze/progress/${id}`)

// Chat: fetch + ReadableStream
const res = await fetch('/chat', { method: 'POST', ... })
const reader = res.body.getReader()
while (true) {
  const { done, value } = await reader.read()
  // accumulate chunks, update UI
}
```

---

## Common interview questions — prepared answers

**Q: Why not use OpenAI for everything?**
A: Cost. At 1K analyses/day, OpenAI embeddings + GPT-4o = ~$20/day. Our stack = ~$0/day. For a startup validating product-market fit, that difference is 10+ months of free runway.

**Q: What breaks first at scale?**
A: Whisper transcription. It's synchronous and CPU-bound (~30s per video). Solution: move to a task queue (Celery/Redis) with multiple worker processes. Each worker loads Whisper once at startup.

**Q: Why chunk size 500 tokens?**
A: BGE's max input is 512 tokens. 500 leaves room for prefix prompting. Overlap of 100 prevents losing context at boundaries. For short-form videos (60s), most transcripts fit in 1-3 chunks anyway.

**Q: How do you prevent hallucination in the chat?**
A: The system prompt enforces citation rules: "Never make a claim without citing [A-Chunk-N] or [B-Chunk-N]." The retrieved context is included verbatim. The LLM can only reference content that was actually retrieved — it doesn't need to invent anything.

**Q: Why LangGraph instead of plain LangChain?**
A: LangGraph gives us a stateful graph with built-in checkpointing. One line — `MemorySaver()` — handles multi-turn conversation memory. With plain LangChain, we'd need to manually pass message history in every call.

**Q: How do you handle Instagram rate limiting?**
A: We use yt-dlp (which rotates user agents and handles redirects) for download, and instaloader (which makes standard browser requests) for profile data. For public profiles, both work reliably. We also cache: same URL = same video record = never re-scraped.

**Q: What's the engagement rate formula?**
A: `(likes + comments) / views × 100`. This normalizes for audience size. A 5% rate is strong (1 in 20 viewers actively engaged). Below 1% means the content didn't resonate despite the reach.
