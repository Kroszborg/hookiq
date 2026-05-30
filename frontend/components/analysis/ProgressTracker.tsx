"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useProgress } from "@/hooks/useProgress";

const STEPS = [
  "Extracting metadata",
  "Fetching transcript",
  "Processing content",
  "Generating embeddings",
  "Storing vectors",
  "Building intelligence",
];

interface Props {
  analysisId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

export function ProgressTracker({ analysisId, onComplete, onError }: Props) {
  const { steps, isDone } = useProgress(analysisId, onComplete, onError);
  const currentIdx = steps.length > 0 ? Math.max(...steps.map((s) => s.index)) : -1;

  return (
    <div className="space-y-3">
      {STEPS.map((label, i) => {
        const done = steps.some((s) => s.index === i);
        const active = currentIdx === i && !isDone;

        return (
          <div key={label} className="flex items-center gap-3">
            <div className="h-5 w-5 shrink-0 flex items-center justify-center">
              {done ? (
                <motion.svg
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="h-3.5 w-3.5 text-emerald-400"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </motion.svg>
              ) : active ? (
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
              ) : (
                <span className="h-1 w-1 rounded-full bg-white/15" />
              )}
            </div>
            <span className={`text-sm transition-colors duration-300 ${done ? "text-foreground" : active ? "text-foreground" : "text-muted-foreground/30"}`}>
              {label}
            </span>
            {active && (
              <span className="font-mono text-[9px] text-muted-foreground/50 tracking-widest ml-auto animate-pulse">
                RUNNING
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
