"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { startAnalysis } from "@/lib/api";
import { detectPlatform } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const FADE_UP = {
  hidden: { opacity: 0, y: 16 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5, ease: "easeOut" as const } }),
};

function PlatformDot({ url }: { url: string }) {
  const p = detectPlatform(url);
  return (
    <span className={`inline-block h-1.5 w-1.5 rounded-full transition-colors ${p === "youtube" ? "bg-red-400" : p === "instagram" ? "bg-pink-400" : "bg-white/20"}`} />
  );
}

export default function HomePage() {
  const router = useRouter();
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!urlA.trim() || !urlB.trim()) {
      setError("Paste both video URLs to begin.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const { analysis_id } = await startAnalysis(urlA.trim(), urlB.trim());
      router.push(`/analysis/${analysis_id}`);
    } catch {
      setError("Could not connect to server. Is the backend running?");
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleAnalyze();
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Top nav */}
      <nav className="flex items-center justify-between px-6 py-5 border-b border-border/40">
        <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">HookIQ</span>
        <div className="flex items-center gap-4 text-xs text-muted-foreground font-medium">
          <a href="#how-it-works" className="hover:text-foreground transition-colors">How it works</a>
          <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
          <ThemeToggle />
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <div className="w-full max-w-xl mx-auto space-y-12">

          {/* Headline */}
          <div className="space-y-4">
            <motion.p
              custom={0}
              variants={FADE_UP}
              initial="hidden"
              animate="show"
              className="font-mono text-[10px] tracking-[0.2em] text-muted-foreground uppercase"
            >
              AI Video Intelligence
            </motion.p>

            <motion.h1
              custom={1}
              variants={FADE_UP}
              initial="hidden"
              animate="show"
              className="text-[2.6rem] sm:text-5xl font-light leading-[1.08] tracking-[-0.03em]"
            >
              <span className="font-display italic">Understand</span> why one<br />
              video works.{" "}
              <span className="text-muted-foreground">The other doesn&apos;t.</span>
            </motion.h1>

            <motion.p
              custom={2}
              variants={FADE_UP}
              initial="hidden"
              animate="show"
              className="text-sm text-muted-foreground leading-relaxed max-w-md"
            >
              Paste two video URLs. Get transcript analysis, engagement breakdown,
              hook scoring, and an AI you can chat with about both — with source citations.
            </motion.p>
          </div>

          {/* Input form */}
          <motion.div
            custom={3}
            variants={FADE_UP}
            initial="hidden"
            animate="show"
            className="space-y-3"
          >
            {/* Video A */}
            <div className="group relative">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none">
                <PlatformDot url={urlA} />
                <span className="font-mono text-[10px] text-muted-foreground/60 tracking-wider">A</span>
              </div>
              <input
                value={urlA}
                onChange={(e) => setUrlA(e.target.value)}
                onKeyDown={handleKey}
                placeholder="youtube.com/shorts/... or instagram.com/reel/..."
                disabled={loading}
                className="w-full h-12 bg-white/[0.04] border border-white/[0.07] hover:border-white/[0.12] focus:border-white/20 rounded-lg pl-12 pr-4 text-sm text-foreground placeholder:text-muted-foreground/40 outline-none transition-all font-mono"
              />
            </div>

            {/* Video B */}
            <div className="group relative">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none">
                <PlatformDot url={urlB} />
                <span className="font-mono text-[10px] text-muted-foreground/60 tracking-wider">B</span>
              </div>
              <input
                value={urlB}
                onChange={(e) => setUrlB(e.target.value)}
                onKeyDown={handleKey}
                placeholder="youtube.com/shorts/... or instagram.com/reel/..."
                disabled={loading}
                className="w-full h-12 bg-white/[0.04] border border-white/[0.07] hover:border-white/[0.12] focus:border-white/20 rounded-lg pl-12 pr-4 text-sm text-foreground placeholder:text-muted-foreground/40 outline-none transition-all font-mono"
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs text-red-400 font-mono">{error}</p>
            )}

            {/* CTA */}
            <button
              onClick={handleAnalyze}
              disabled={loading || !urlA.trim() || !urlB.trim()}
              className="w-full h-12 bg-foreground text-background text-sm font-semibold rounded-lg transition-all hover:bg-white/90 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="h-3.5 w-3.5 border-2 border-background/40 border-t-background rounded-full animate-spin" />
                  <span>Starting analysis…</span>
                </>
              ) : (
                <>
                  Analyze Both Videos
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </>
              )}
            </button>

            <p className="text-[11px] text-muted-foreground/50 text-center font-mono">
              YouTube Shorts · Instagram Reels · TikTok
            </p>
          </motion.div>

          {/* Feature list */}
          <motion.div
            custom={4}
            variants={FADE_UP}
            initial="hidden"
            animate="show"
          >
            <div id="how-it-works" className="border-t border-border/40 pt-8 grid grid-cols-2 gap-x-6 gap-y-5">
              {[
                { label: "Transcript extraction", desc: "From captions or Whisper audio transcription" },
                { label: "Engagement analysis", desc: "Likes, views, comments, follower count, rate" },
                { label: "Hook scoring", desc: "First-5s curiosity, emotion, clarity, retention" },
                { label: "Viral patterns", desc: "Curiosity gap, open loop, social proof, urgency" },
                { label: "LangGraph RAG chat", desc: "Streaming answers with chunk-level citations" },
                { label: "Conversation memory", desc: "Ask follow-ups — context is preserved" },
              ].map((f) => (
                <div key={f.label} className="space-y-0.5">
                  <p className="text-xs font-semibold text-foreground">{f.label}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 px-6 py-4 flex items-center justify-between">
        <span className="font-mono text-[10px] text-muted-foreground/40 tracking-wider">
          HOOKIQ · RAG-POWERED VIDEO ANALYSIS
        </span>
        <span className="font-mono text-[10px] text-muted-foreground/30">
          Groq LLaMA 3.3 · LangGraph · Qdrant · BGE Embeddings
        </span>
      </footer>
    </div>
  );
}
