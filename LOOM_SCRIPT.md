# HookIQ — Loom Demo Script
> Target: 5–7 minutes. Record fresh — no cached URLs.

---

## SETUP BEFORE RECORDING

1. Open two browser tabs:
   - Tab 1: `http://localhost:3000` (or your live URL)
   - Tab 2: YouTube — find a viral Short you haven't analyzed yet
   - Tab 3: Instagram — find a public Reel on a similar topic

2. Have these ready to paste:
   - YouTube Short URL (e.g. a food/lifestyle/trending Short with >100K views)
   - Instagram Reel URL (public, from a creator account)

3. Keep Docker logs visible in terminal (so viewers can see backend working)

---

## SCRIPT

---

### [0:00 – 0:30] INTRO

> "Hey, I'm [Name]. This is HookIQ — an AI tool I built that tells creators exactly why one video went viral and another didn't.
>
> You give it two video URLs — YouTube Shorts, Instagram Reels, or TikTok — and it returns transcript analysis, engagement breakdown, hook scoring, viral pattern detection, and an AI you can actually have a conversation with about both videos, with real citations back to the transcript.
>
> Let me show you how it works from scratch."

---

### [0:30 – 1:00] INPUT

> *(Show the homepage)*
>
> "Here's the app. I'll paste two fresh URLs I haven't analyzed before — a YouTube Short here, and an Instagram Reel here.
>
> I'll hit Analyze."

*(Paste URLs, click Analyze)*

---

### [1:00 – 2:00] PROCESSING (talk while waiting)

> *(Progress screen animating)*
>
> "While this runs, let me explain what's happening. For the YouTube video, we're pulling captions directly from YouTube's caption API — instant, no download needed. For the Instagram Reel, we're using yt-dlp to download the audio, then running it through faster-whisper for local transcription. No Deepgram, no paid API — runs right in the Docker container.
>
> The metadata — views, likes, comments, followers, upload date, hashtags — comes from yt-dlp for both platforms.
>
> Then we chunk the transcripts into 500-token segments with 100-token overlap, embed them using BAAI/bge-small — a 384-dimension model that outperforms OpenAI's text-embedding-3-small on retrieval tasks at zero cost — and store them in Qdrant, tagged with the video ID.
>
> Finally, we run 8 sequential Groq LLaMA 3.3 calls for the intelligence layer: hook scoring, structure analysis, viral pattern detection, comparison, and 5 specific recommendations."

*(Analysis completes)*

---

### [2:00 – 3:30] DASHBOARD TOUR

> *(Dashboard visible)*
>
> "Okay, analysis complete. Let me walk through what we got.

**Video Cards:**
> "Each card shows the real data — views, likes, comments, follower count, upload date, hashtags. For Instagram, views are sometimes unavailable because Instagram restricts API access without auth cookies. We fall back to showing raw interactions instead.
>
> Each card also shows a Viral Score — my composite metric from 0 to 100. It combines the hook quality scores, viral pattern count, and normalized engagement rate."

**Content Timeline:**
> *(Scroll to timeline)*
> "This is the Content Timeline — the AI identified four structural segments: Hook, Story, Value Delivery, and CTA, with realistic timestamps based on the actual transcript. You can hover to see what's happening at each point."

**Transcript Viewer:**
> *(Expand transcript on one card)*
> "If I expand the transcript, you see the actual transcribed content — color-coded by which segment it falls in. Purple is the Hook. This is real data from the Whisper transcription, not a summary."

**Hook Callout:**
> *(Scroll to insights panel)*
> "'What stopped the scroll' — this is the first 5 seconds of actual spoken transcript. This is the line that made someone not swipe. For Video A it's... [read it]. For Video B it's... [read it]."

**Hook Analysis & Viral Patterns:**
> "Hook analysis scores four dimensions from 0 to 10 — curiosity, emotional resonance, clarity, and retention potential — all from the actual transcript content.
>
> Viral patterns — 6 psychological patterns: curiosity gap, open loop, social proof, authority, urgency, novelty. These are detected from the transcript with specific evidence quoted."

**Performance Benchmark:**
> "And the performance benchmark shows both videos' scores against each other and against the ~3.5% industry average engagement rate."

---

### [3:30 – 5:00] RAG CHAT

> *(Switch to Chat tab)*
>
> "Now the interesting part — the chat. This is a full RAG system built on LangGraph. Let me ask something real."

*(Type: "Why did Video B outperform Video A?")*

> *(Wait for response)*
>
> "Notice the citation tags — [B-Chunk-0], [A-Chunk-1]. These aren't made up. Let me show you what they reference."

*(Show that the citations correspond to actual transcript content)*

> "Every claim is grounded in the actual transcript chunks retrieved from Qdrant via vector search."

*(Type a follow-up: "What specific hook technique should I steal from Video B?")*

> "Notice I didn't re-explain the context — it remembers. This is LangGraph's MemorySaver checkpointing, keyed by session ID. It replays the full conversation state on every turn."

*(Response streams in)*

> "Streaming via Server-Sent Events — no WebSocket needed, works through any proxy."

*(Type: "Who created Video A and what's their follower count?")*

> "It can answer metadata questions too — the metadata is part of the system prompt context, alongside the retrieved chunks."

---

### [5:00 – 5:45] TECHNICAL DECISIONS

> "Let me talk quickly about why I chose each component — because for 1,000 creators a day, cost and scale matter.

**Groq LLaMA 3.3 70B** — free tier, 30 requests per minute, 14,400 per day. At 8 calls per analysis, that's 1,800 analyses per day at zero cost. Gemini Flash is an alternative — I have both wired in via an environment variable.

**BGE-small-en-v1.5** — runs locally in the container, 384-dim vectors, comparable retrieval quality to OpenAI's embedding API at literally zero cost. At 1,000 analyses per day, OpenAI embeddings would cost ~$4/day. BGE costs nothing.

**Qdrant self-hosted** — persistent Docker volume, no API cost, fast cosine search with payload filtering by analysis_id and video label. Pinecone's free tier caps at 100K vectors — one week of production usage.

**URL caching** — the same URL analyzed twice skips the entire pipeline. SHA-256 hash check against the database before any extraction runs. Repeat analyses are instant.

**At 10,000 creators/day** — add a Redis/Celery task queue, upgrade the VM, switch SQLite to PostgreSQL. The architecture handles it without re-writing the core."

---

### [5:45 – 6:15] SHARING

> *(Click Share →)*
>
> "Every analysis generates a shareable report at /report/[id] with proper OpenGraph meta tags — title, description, thumbnail — so it looks good when shared on Slack or Twitter.
>
> The report shows the full dashboard without the chat — clean enough to send to a client."

*(Show the report page)*

---

### [6:15 – 6:30] CLOSE

> "So: real transcription, real vector search, real citations, real memory — nothing hardcoded. The whole stack runs in Docker Compose on a $0 GCP VM with a free Vercel frontend.
>
> Questions on the architecture or the choices — happy to discuss live."

---

## BACKUP QUESTIONS (in case they ask)

**"How does the RAG actually work?"**
> "User message → BGE embed → Qdrant cosine search, top-5 chunks per video filtered by analysis_id + label → chunks injected into LangGraph system prompt → Groq LLaMA streams the answer. Citations are tag matches between the response text and the chunk tags."

**"Why not just use GPT-4 for everything?"**
> "Cost. At 8 Groq calls per analysis, we're at $0. At 8 GPT-4o calls, we're at roughly $0.40–0.80 per analysis. At 1,000 analyses/day that's $300–600/month. The quality difference doesn't justify it for structured JSON extraction."

**"What happens with Instagram views=N/A?"**
> "Instagram restricts view counts via their CDN API without authenticated session cookies. This is a platform-level restriction. In production, we'd add Instagram Basic Display API for verified business accounts. The system gracefully falls back to showing raw interaction counts (likes + comments) and skips the engagement rate calculation rather than showing a wrong number."

**"Is this production-ready?"**
> "For a demo and small scale — yes. For large scale we'd add: authenticated users, rate limiting per user, Celery task queue, PostgreSQL instead of SQLite, and proper SSL. The current architecture handles a few hundred analyses/day comfortably."
