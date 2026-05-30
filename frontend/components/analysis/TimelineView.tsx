"use client";

import { useState } from "react";
import type { StructureSegment } from "@/types";

const SEG: Record<string, { bg: string; text: string }> = {
  Hook:  { bg: "bg-white", text: "text-background" },
  Story: { bg: "bg-white/50", text: "text-background" },
  Value: { bg: "bg-white/25", text: "text-foreground" },
  CTA:   { bg: "bg-white/10", text: "text-foreground" },
};

interface Props {
  segments: StructureSegment[];
  duration: number;
  label: "A" | "B";
}

export function TimelineView({ segments, duration, label }: Props) {
  const [hovered, setHovered] = useState<StructureSegment | null>(null);
  const total = duration || 60;

  return (
    <div className="space-y-3">
      <p className="font-mono text-[9px] text-muted-foreground/50 tracking-widest uppercase">Video {label}</p>

      {/* Bar */}
      <div className="flex h-5 gap-px rounded overflow-hidden bg-white/[0.03]">
        {segments.map((seg, i) => {
          const w = ((seg.end_time - seg.start_time) / total) * 100;
          const c = SEG[seg.segment] ?? SEG.Hook;
          return (
            <div
              key={i}
              style={{ width: `${Math.max(w, 4)}%` }}
              className={`${c.bg} cursor-pointer hover:opacity-100 opacity-80 transition-opacity`}
              onMouseEnter={() => setHovered(seg)}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}
      </div>

      {/* Tooltip */}
      {hovered ? (
        <div className="bg-white/[0.03] border border-border/40 rounded-lg px-3 py-2.5 text-xs space-y-1">
          <p className="font-semibold">{hovered.segment} · {hovered.start_time.toFixed(0)}s – {hovered.end_time.toFixed(0)}s</p>
          <p className="text-muted-foreground leading-relaxed">{hovered.summary}</p>
        </div>
      ) : (
        <div className="flex gap-4">
          {segments.map((seg) => {
            const c = SEG[seg.segment] ?? SEG.Hook;
            return (
              <div key={seg.segment} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <div className={`h-2 w-2 rounded-sm ${c.bg}`} />
                {seg.segment}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
