"use client";

import { useState } from "react";
import type { StructureSegment } from "@/types";

const SEG_COLORS: Record<string, string> = {
  hook: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  story: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  value: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  cta: "bg-orange-500/20 text-orange-300 border-orange-500/30",
};

function getSegmentForTime(time: number, segments: StructureSegment[]): StructureSegment | null {
  return segments.find(s => time >= s.start_time && time <= s.end_time) ?? null;
}

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface Props {
  transcript: string | null;
  transcriptSegments?: TranscriptSegment[];
  structureSegments?: StructureSegment[];
  label: "A" | "B";
}

export function TranscriptViewer({ transcript, transcriptSegments = [], structureSegments = [], label }: Props) {
  const [open, setOpen] = useState(false);

  if (!transcript) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground/50 hover:text-muted-foreground uppercase tracking-widest transition-colors"
      >
        <svg
          className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Transcript
      </button>

      {open && (
        <div className="mt-2 bg-white/[0.02] border border-border/30 rounded-lg p-3 max-h-48 overflow-y-auto">
          {transcriptSegments.length > 0 ? (
            <div className="space-y-1.5">
              {transcriptSegments.map((seg, i) => {
                const structure = getSegmentForTime(seg.start, structureSegments);
                const colorClass = structure
                  ? SEG_COLORS[structure.segment.toLowerCase()] ?? ""
                  : "";
                return (
                  <div key={i} className="flex gap-2 items-start">
                    <span className="font-mono text-[9px] text-muted-foreground/40 shrink-0 mt-0.5 w-10 text-right">
                      {Math.floor(seg.start)}s
                    </span>
                    <span
                      className={`text-xs leading-relaxed ${colorClass ? `px-1.5 rounded border ${colorClass}` : "text-muted-foreground"}`}
                    >
                      {seg.text}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground leading-relaxed">{transcript}</p>
          )}
        </div>
      )}
    </div>
  );
}
