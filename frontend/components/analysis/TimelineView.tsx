"use client";

import { useState } from "react";
import type { StructureSegment } from "@/types";

const SEG: Record<string, { bg: string; label: string; dot: string }> = {
  hook:  { bg: "bg-purple-500",  label: "Hook",  dot: "bg-purple-500" },
  story: { bg: "bg-blue-500",    label: "Story", dot: "bg-blue-500" },
  value: { bg: "bg-emerald-500", label: "Value", dot: "bg-emerald-500" },
  cta:   { bg: "bg-orange-500",  label: "CTA",   dot: "bg-orange-500" },
};

const DEFAULT: typeof SEG[string] = { bg: "bg-zinc-500", label: "Segment", dot: "bg-zinc-500" };

// Normalise to lowercase so we handle "Hook", "hook", "HOOK" etc.
function getSegStyle(segment: string) {
  return SEG[segment.toLowerCase()] ?? DEFAULT;
}

interface Props {
  segments: StructureSegment[];
  duration: number;
  label: "A" | "B";
}

export function TimelineView({ segments, duration, label }: Props) {
  const [hovered, setHovered] = useState<StructureSegment | null>(null);
  const total = Math.max(duration || 60, segments[segments.length - 1]?.end_time || 60);

  if (!segments || segments.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="font-mono text-[9px] text-muted-foreground/50 tracking-widest uppercase">Video {label}</p>

      {/* Timeline bar */}
      <div className="flex h-6 rounded-lg overflow-hidden gap-0.5 bg-white/[0.03] border border-border/30">
        {segments.map((seg, i) => {
          const w = ((seg.end_time - seg.start_time) / total) * 100;
          const c = getSegStyle(seg.segment);
          return (
            <div
              key={i}
              style={{ width: `${Math.max(w, 6)}%` }}
              className={`${c.bg} cursor-pointer transition-opacity hover:opacity-90 opacity-75 flex items-center justify-center`}
              onMouseEnter={() => setHovered(seg)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="text-[8px] font-bold text-white/80 truncate px-1 hidden sm:block select-none">
                {seg.segment}
              </span>
            </div>
          );
        })}
      </div>

      {/* Tooltip on hover */}
      {hovered && (
        <div className="bg-popover border border-border/50 rounded-lg p-2.5 text-xs space-y-0.5">
          <div className={`font-semibold flex items-center gap-1.5`}>
            <span className={`h-2 w-2 rounded-sm ${getSegStyle(hovered.segment).dot}`} />
            {hovered.segment} · {hovered.start_time.toFixed(0)}s – {hovered.end_time.toFixed(0)}s
          </div>
          <p className="text-muted-foreground leading-relaxed">{hovered.summary}</p>
        </div>
      )}

      {/* Legend */}
      {!hovered && (
        <div className="flex flex-wrap gap-3">
          {segments.map((seg, i) => {
            const c = getSegStyle(seg.segment);
            return (
              <div key={i} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className={`h-2 w-2 rounded-sm ${c.dot}`} />
                {c.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
