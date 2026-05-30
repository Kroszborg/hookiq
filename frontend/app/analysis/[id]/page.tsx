"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { use } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ProgressTracker } from "@/components/analysis/ProgressTracker";
import { VideoCard } from "@/components/analysis/VideoCard";
import { InsightsPanel } from "@/components/analysis/InsightsPanel";
import { TimelineView } from "@/components/analysis/TimelineView";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { getAnalysis } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Analysis } from "@/types";

interface Props {
  params: Promise<{ id: string }>;
}

type Phase = "loading" | "processing" | "complete" | "error";

export default function AnalysisPage({ params }: Props) {
  const { id } = use(params);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"insights" | "chat">("insights");

  useEffect(() => {
    getAnalysis(id)
      .then((data) => {
        setAnalysis(data);
        if (data.status === "complete") setPhase("complete");
        else if (data.status === "failed") { setPhase("error"); setErrorMsg(data.error_message || "Analysis failed."); }
        else setPhase("processing");
      })
      .catch(() => { setPhase("error"); setErrorMsg("Could not load analysis."); });
  }, [id]);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-4 border-b border-border/40 shrink-0">
        <Link href="/" className="font-mono text-xs tracking-widest text-muted-foreground hover:text-foreground uppercase transition-colors">
          HookIQ
        </Link>
        <div className="flex items-center gap-4">
          {phase === "complete" && (
            <Link href={`/report/${id}`} className="font-mono text-[10px] tracking-wider text-muted-foreground hover:text-foreground uppercase transition-colors">
              Share →
            </Link>
          )}
          <ThemeToggle />
          <span className={`font-mono text-[10px] tracking-wider uppercase ${phase === "complete" ? "text-emerald-500" : phase === "error" ? "text-red-400" : "text-muted-foreground/50"}`}>
            {phase === "loading" ? "—" : phase === "processing" ? "Processing" : phase === "complete" ? "Complete" : "Failed"}
          </span>
        </div>
      </header>

      {/* Loading */}
      {phase === "loading" && (
        <div className="flex-1 flex items-center justify-center">
          <div className="h-5 w-5 border border-white/20 border-t-white/60 rounded-full animate-spin" />
        </div>
      )}

      {/* Processing */}
      {phase === "processing" && (
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm space-y-8">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Analyzing your videos</h2>
              <p className="text-sm text-muted-foreground">This takes 30–90 seconds depending on video length.</p>
            </div>
            <ProgressTracker
              analysisId={id}
              onComplete={() => getAnalysis(id).then(d => { setAnalysis(d); setPhase("complete"); })}
              onError={(e) => { setPhase("error"); setErrorMsg(e); }}
            />
          </motion.div>
        </div>
      )}

      {/* Error */}
      {phase === "error" && (
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-20 space-y-3">
          <p className="text-sm text-red-400 font-mono">{errorMsg}</p>
          <Link href="/" className="text-xs text-muted-foreground hover:text-foreground underline transition-colors">
            ← Try again
          </Link>
        </div>
      )}

      {/* Complete — main dashboard */}
      <AnimatePresence>
        {phase === "complete" && analysis && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 flex flex-col lg:flex-row overflow-hidden"
          >
            {/* Left: video cards + timelines */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Video cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {analysis.video_a && <VideoCard video={analysis.video_a} label="A" />}
                {analysis.video_b && <VideoCard video={analysis.video_b} label="B" />}
              </div>

              {/* Timelines */}
              {(analysis.structure_a || analysis.structure_b) && (
                <div className="bg-white/[0.02] border border-border/40 rounded-xl p-5 space-y-5">
                  <p className="font-mono text-[10px] tracking-widest text-muted-foreground uppercase">Content Timeline</p>
                  <div className="space-y-5">
                    {analysis.structure_a && analysis.video_a && (
                      <TimelineView segments={analysis.structure_a} duration={analysis.video_a.duration || 60} label="A" />
                    )}
                    {analysis.structure_b && analysis.video_b && (
                      <TimelineView segments={analysis.structure_b} duration={analysis.video_b.duration || 60} label="B" />
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right panel */}
            <div className="w-full lg:w-[380px] border-t lg:border-t-0 lg:border-l border-border/40 flex flex-col">
              {/* Tab bar */}
              <div className="flex border-b border-border/40 shrink-0">
                {(["insights", "chat"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 py-3 font-mono text-[10px] tracking-widest uppercase transition-colors ${activeTab === tab ? "text-foreground border-b border-foreground" : "text-muted-foreground hover:text-foreground"}`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {activeTab === "insights" && (
                <div className="flex-1 overflow-y-auto p-4">
                  <InsightsPanel analysis={analysis} />
                </div>
              )}

              {activeTab === "chat" && (
                <div className="flex-1 flex flex-col overflow-hidden" style={{ height: "calc(100vh - 9rem)" }}>
                  <ChatPanel analysisId={id} />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
