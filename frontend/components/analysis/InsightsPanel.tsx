"use client";

import { cn } from "@/lib/utils";
import type { Analysis, HookAnalysis, ViralPatterns } from "@/types";

interface Props {
  analysis: Analysis;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[9px] tracking-[0.18em] text-muted-foreground/50 uppercase mb-3">{children}</p>
  );
}

function HookScores({ hook, color }: { hook: HookAnalysis; color: string }) {
  const scores = [
    { key: "curiosity_score", label: "Curiosity" },
    { key: "emotional_score", label: "Emotional" },
    { key: "clarity_score", label: "Clarity" },
    { key: "retention_potential", label: "Retention" },
  ];
  return (
    <div className="space-y-2">
      {scores.map(({ key, label }) => {
        const val = (hook as unknown as Record<string, number>)[key] ?? 0;
        return (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{label}</span>
              <span className={`font-mono font-semibold ${color}`}>{val}/10</span>
            </div>
            <div className="h-px bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${color === "text-white" ? "bg-white" : color === "text-white/60" ? "bg-white/40" : "bg-white/70"}`}
                style={{ width: `${val * 10}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ViralPatternGrid({ patterns }: { patterns: ViralPatterns }) {
  const items = [
    { key: "curiosity_gap", label: "Curiosity Gap" },
    { key: "open_loop", label: "Open Loop" },
    { key: "social_proof", label: "Social Proof" },
    { key: "authority", label: "Authority" },
    { key: "urgency", label: "Urgency" },
    { key: "novelty", label: "Novelty" },
  ];
  return (
    <div className="grid grid-cols-2 gap-1.5">
      {items.map(({ key, label }) => {
        const p = patterns[key as keyof ViralPatterns];
        return (
          <div
            key={key}
            className={cn(
              "rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors",
              p.present
                ? "bg-white/[0.04] border-white/[0.1] text-foreground"
                : "bg-transparent border-border/30 text-muted-foreground/40"
            )}
          >
            <span className="mr-1">{p.present ? "✓" : "○"}</span>
            {label}
          </div>
        );
      })}
    </div>
  );
}

export function InsightsPanel({ analysis }: Props) {
  const { hook_analysis_a, hook_analysis_b, viral_patterns_a, viral_patterns_b, recommendations, comparison_insights } = analysis;

  return (
    <div className="space-y-6">

      {/* Winner */}
      {comparison_insights && (
        <div className="space-y-3">
          <SectionLabel>Performance summary</SectionLabel>
          <div className="bg-white/[0.02] border border-border/40 rounded-xl p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Winner</p>
                <p className="text-2xl font-semibold font-display italic">
                  {comparison_insights.winner === "tie" ? "Tied" : `Video ${comparison_insights.winner}`}
                </p>
              </div>
              {comparison_insights.performance_delta_pct > 0 && (
                <span className="font-mono text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded-lg shrink-0">
                  +{comparison_insights.performance_delta_pct.toFixed(1)}% ER
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{comparison_insights.summary}</p>
            <div className="pt-1 space-y-2 text-xs border-t border-border/30">
              <p className="text-muted-foreground leading-relaxed">
                <span className="text-foreground font-medium">Hook: </span>
                {comparison_insights.hook_comparison}
              </p>
              <p className="text-muted-foreground leading-relaxed">
                <span className="text-foreground font-medium">Content: </span>
                {comparison_insights.content_comparison}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Hook analysis */}
      {(hook_analysis_a || hook_analysis_b) && (
        <div className="space-y-3">
          <SectionLabel>Hook analysis (first 5s)</SectionLabel>
          <div className="grid grid-cols-2 gap-3">
            {hook_analysis_a && (
              <div className="bg-white/[0.02] border border-border/40 rounded-xl p-3 space-y-2">
                <p className="font-mono text-[9px] text-muted-foreground/50 tracking-widest uppercase">Video A</p>
                <HookScores hook={hook_analysis_a} color="text-white" />
                {hook_analysis_a.summary && (
                  <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">{hook_analysis_a.summary}</p>
                )}
              </div>
            )}
            {hook_analysis_b && (
              <div className="bg-white/[0.02] border border-border/40 rounded-xl p-3 space-y-2">
                <p className="font-mono text-[9px] text-muted-foreground/50 tracking-widest uppercase">Video B</p>
                <HookScores hook={hook_analysis_b} color="text-white/60" />
                {hook_analysis_b.summary && (
                  <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">{hook_analysis_b.summary}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Viral patterns */}
      {(viral_patterns_a || viral_patterns_b) && (
        <div className="space-y-3">
          <SectionLabel>Viral patterns</SectionLabel>
          <div className="space-y-3">
            {viral_patterns_a && (
              <div>
                <p className="font-mono text-[9px] text-muted-foreground/40 tracking-widest uppercase mb-2">Video A</p>
                <ViralPatternGrid patterns={viral_patterns_a} />
              </div>
            )}
            {viral_patterns_b && (
              <div>
                <p className="font-mono text-[9px] text-muted-foreground/40 tracking-widest uppercase mb-2">Video B</p>
                <ViralPatternGrid patterns={viral_patterns_b} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="space-y-3">
          <SectionLabel>Improvements for Video B</SectionLabel>
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <div key={rec.rank} className="bg-white/[0.02] border border-border/40 rounded-xl p-3.5 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground/40 w-4">{rec.rank}.</span>
                  <span className="text-xs font-semibold">{rec.title}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed pl-6">{rec.action}</p>
                <p className="text-[11px] text-muted-foreground/50 italic leading-relaxed pl-6">
                  From A: {rec.evidence_from_a}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
