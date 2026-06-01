"use client";

import { useState } from "react";
import type { StructureSegment } from "@/types";

const SEG_STYLES: Record<string, { dot: string; text: string; bg: string }> = {
  hook:  { dot: "bg-purple-500", text: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
  story: { dot: "bg-blue-500",   text: "text-blue-400",   bg: "bg-blue-500/10 border-blue-500/20" },
  value: { dot: "bg-emerald-500",text: "text-emerald-400",bg: "bg-emerald-500/10 border-emerald-500/20" },
  cta:   { dot: "bg-orange-500", text: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20" },
};

function getStructureForTime(t: number, segs: StructureSegment[]) {
  return segs.find((s) => t >= s.start_time && t <= s.end_time);
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

interface TranscriptSeg { start: number; end: number; text: string; }

interface Props {
  transcript?: string | null;
  transcriptSegments?: TranscriptSeg[] | null;
  structureSegments?: StructureSegment[] | null;
  label: "A" | "B";
}

export function TranscriptViewer({ transcript, transcriptSegments, structureSegments, label }: Props) {
  const [open, setOpen] = useState(false);

  if (!transcript && (!transcriptSegments || transcriptSegments.length === 0)) return null;

  const timedSegs = transcriptSegments && transcriptSegments.length > 0 ? transcriptSegments : null;

  return (
    <div className="mt-3 border-t border-border/20 pt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/50 hover:text-muted-foreground uppercase tracking-widest transition-colors w-full"
      >
        <svg className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Transcript · Video {label}
        <span className="ml-auto text-muted-foreground/30">
          {timedSegs ? `${timedSegs.length} segments` : "text"}
        </span>
      </button>

      {open && (
        <div className="mt-2 bg-white/[0.015] border border-border/20 rounded-lg p-3 max-h-56 overflow-y-auto space-y-1.5">
          {timedSegs ? (
            timedSegs.map((seg, i) => {
              const structure = structureSegments ? getStructureForTime(seg.start, structureSegments) : null;
              const style = structure ? SEG_STYLES[structure.segment.toLowerCase()] : null;
              return (
                <div key={i} className="flex gap-2 items-start text-xs">
                  <span className="font-mono text-[9px] text-muted-foreground/40 shrink-0 w-8 text-right mt-0.5">
                    {formatTime(seg.start)}
                  </span>
                  {style ? (
                    <span className={`px-1.5 py-0.5 rounded border text-[11px] leading-relaxed ${style.bg} ${style.text}`}>
                      {seg.text}
                    </span>
                  ) : (
                    <span className="text-muted-foreground leading-relaxed text-[11px]">{seg.text}</span>
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-xs text-muted-foreground leading-relaxed">{transcript}</p>
          )}
        </div>
      )}
    </div>
  );
}
