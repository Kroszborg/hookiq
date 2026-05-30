import { use } from "react";
import Link from "next/link";
import { getAnalysis } from "@/lib/api";
import { VideoCard } from "@/components/analysis/VideoCard";
import { InsightsPanel } from "@/components/analysis/InsightsPanel";
import { TimelineView } from "@/components/analysis/TimelineView";
import type { Analysis } from "@/types";

interface Props {
  params: Promise<{ id: string }>;
}

function ShareButton({ id }: { id: string }) {
  return (
    <button
      onClick={() => navigator.clipboard.writeText(window.location.href)}
      className="text-xs border border-border/40 hover:border-border/70 px-3 py-1.5 rounded-lg text-muted-foreground hover:text-foreground transition-all"
    >
      Copy Link
    </button>
  );
}

export default async function ReportPage({ params }: Props) {
  const { id } = await params;

  let analysis: Analysis | null = null;
  let error: string | null = null;

  try {
    analysis = await getAnalysis(id);
  } catch {
    error = "Could not load this report.";
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border/50 px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-6 w-6 rounded bg-primary/20 border border-primary/30 flex items-center justify-center">
            <span className="text-[9px] font-black text-primary">IQ</span>
          </div>
          <span className="text-sm font-bold">HookIQ</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Shared Report</span>
          {/* ShareButton needs 'use client' for clipboard — use a separate component */}
        </div>
      </header>

      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-destructive text-sm">{error}</p>
        </div>
      ) : !analysis || analysis.status !== "complete" ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground text-sm">Report not yet available.</p>
        </div>
      ) : (
        <main className="max-w-5xl mx-auto w-full px-4 py-8 space-y-8">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold">Video Comparison Report</h1>
            <p className="text-sm text-muted-foreground">
              {analysis.video_a?.creator || "Video A"} vs {analysis.video_b?.creator || "Video B"}
            </p>
            <Link
              href={`/analysis/${id}`}
              className="text-xs text-primary hover:underline"
            >
              Open interactive analysis →
            </Link>
          </div>

          {/* Video cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {analysis.video_a && <VideoCard video={analysis.video_a} label="A" />}
            {analysis.video_b && <VideoCard video={analysis.video_b} label="B" />}
          </div>

          {/* Timelines */}
          {(analysis.structure_a || analysis.structure_b) && (
            <div className="bg-card/30 border border-border/40 rounded-xl p-4 space-y-5">
              <h2 className="text-sm font-semibold">Content Timeline</h2>
              {analysis.structure_a && analysis.video_a && (
                <TimelineView
                  segments={analysis.structure_a}
                  duration={analysis.video_a.duration || 60}
                  label="A"
                />
              )}
              {analysis.structure_b && analysis.video_b && (
                <TimelineView
                  segments={analysis.structure_b}
                  duration={analysis.video_b.duration || 60}
                  label="B"
                />
              )}
            </div>
          )}

          {/* Insights */}
          <InsightsPanel analysis={analysis} />

          <div className="text-center pt-4">
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-foreground underline"
            >
              Compare your own videos →
            </Link>
          </div>
        </main>
      )}
    </div>
  );
}
