"use client";

import { cn } from "@/lib/utils";
import type { VideoCard, HookAnalysis, ViralPatterns } from "@/types";

export function computeViralScore(
  video: VideoCard,
  hook: HookAnalysis | null,
  patterns: ViralPatterns | null
): number {
  let score = 0;

  // Hook quality: 0–40 pts (average of 4 dimensions, each 0–10)
  if (hook) {
    const avg = (hook.curiosity_score + hook.emotional_score + hook.clarity_score + hook.retention_potential) / 4;
    score += (avg / 10) * 40;
  } else {
    score += 20; // neutral baseline
  }

  // Viral patterns: 0–30 pts (5 pts per detected pattern)
  if (patterns) {
    const detected = Object.values(patterns).filter((p) => p?.present).length;
    score += (detected / 6) * 30;
  } else {
    score += 15;
  }

  // Engagement rate: 0–30 pts
  const er = video.engagement_rate;
  if (er !== null && er !== undefined) {
    if (er >= 8) score += 30;
    else if (er >= 5) score += 25;
    else if (er >= 2) score += 15;
    else score += 5;
  } else {
    score += 12; // neutral when views unavailable
  }

  return Math.min(100, Math.round(score));
}

function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-400";
  if (score >= 50) return "text-yellow-400";
  return "text-red-400";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Viral Potential";
  if (score >= 65) return "Strong";
  if (score >= 50) return "Average";
  if (score >= 35) return "Weak";
  return "Low";
}

interface Props {
  video: VideoCard;
  hook: HookAnalysis | null;
  patterns: ViralPatterns | null;
  label: "A" | "B";
}

export function ViralScore({ video, hook, patterns, label }: Props) {
  const score = computeViralScore(video, hook, patterns);
  const color = scoreColor(score);
  const circumference = 2 * Math.PI * 20;
  const filled = circumference * (score / 100);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative h-14 w-14">
        <svg className="h-14 w-14 -rotate-90" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" strokeWidth="3"
            className="text-white/[0.06]" />
          <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3"
            className={color}
            strokeDasharray={`${filled} ${circumference - filled}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.8s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-mono text-sm font-bold ${color}`}>{score}</span>
        </div>
      </div>
      <div className="text-center">
        <p className="font-mono text-[9px] text-muted-foreground/50 tracking-widest uppercase">Viral Score</p>
        <p className={`text-[10px] font-semibold ${color}`}>{scoreLabel(score)}</p>
      </div>
    </div>
  );
}
