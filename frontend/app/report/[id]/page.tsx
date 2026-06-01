import type { Metadata } from "next";
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

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const analysis = await getAnalysis(id);
    if (analysis.status === "complete" && analysis.video_a && analysis.video_b) {
      const title = `${analysis.video_a.creator ?? "Video A"} vs ${analysis.video_b.creator ?? "Video B"} — HookIQ`;
      const winner = analysis.comparison_insights?.winner;
      const desc = winner
        ? `Video ${winner} wins with ${analysis.comparison_insights?.performance_delta_pct?.toFixed(1) ?? "?"}% higher engagement. Analyzed by HookIQ.`
        : "AI-powered video comparison — HookIQ";
      return {
        title,
        description: desc,
        openGraph: {
          title,
          description: desc,
          type: "website",
          images: analysis.video_a.thumbnail_url
            ? [{ url: analysis.video_a.thumbnail_url, width: 1280, height: 720 }]
            : [],
        },
        twitter: { card: "summary_large_image", title, description: desc },
      };
    }
  } catch {}
  return { title: "HookIQ Report" };
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
    <div className="min-h-screen flex flex-col bg-background">
      <header className="border-b border-border/50 px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-6 w-6 rounded bg-primary/20 border border-primary/30 flex items-center justify-center">
            <span className="text-[9px] font-black text-primary">IQ</span>
          </div>
          <span className="text-sm font-bold">HookIQ</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Shared Report</span>
          {analysis?.status === "complete" && (
            <Link
              href={`/analysis/${id}`}
              className="text-xs font-medium text-foreground border border-border/50 hover:border-border px-3 py-1.5 rounded-lg transition-all"
            >
              Open Chat →
            </Link>
          )}
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
              {analysis.video_a?.creator ?? "Video A"} vs {analysis.video_b?.creator ?? "Video B"}
            </p>
          </div>

          {/* Video cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {analysis.video_a && (
              <VideoCard
                video={analysis.video_a}
                label="A"
                hook={analysis.hook_analysis_a}
                patterns={analysis.viral_patterns_a}
                structure={analysis.structure_a}
                transcript={analysis.video_a.transcript}
              />
            )}
            {analysis.video_b && (
              <VideoCard
                video={analysis.video_b}
                label="B"
                hook={analysis.hook_analysis_b}
                patterns={analysis.viral_patterns_b}
                structure={analysis.structure_b}
                transcript={analysis.video_b.transcript}
              />
            )}
          </div>

          {/* Timelines */}
          {(analysis.structure_a || analysis.structure_b) && (
            <div className="bg-card/30 border border-border/40 rounded-xl p-4 space-y-5">
              <h2 className="text-sm font-semibold">Content Timeline</h2>
              {analysis.structure_a && analysis.video_a && (
                <TimelineView segments={analysis.structure_a} duration={analysis.video_a.duration || 60} label="A" />
              )}
              {analysis.structure_b && analysis.video_b && (
                <TimelineView segments={analysis.structure_b} duration={analysis.video_b.duration || 60} label="B" />
              )}
            </div>
          )}

          {/* Insights */}
          <InsightsPanel analysis={analysis} />

          <div className="text-center pt-4">
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground underline">
              Compare your own videos →
            </Link>
          </div>
        </main>
      )}
    </div>
  );
}
