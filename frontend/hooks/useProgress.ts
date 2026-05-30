"use client";

import { useEffect, useRef, useState } from "react";
import type { ProgressEvent } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useProgress(
  analysisId: string | null,
  onComplete: () => void,
  onError: (error: string) => void
) {
  const [steps, setSteps] = useState<ProgressEvent[]>([]);
  const [isDone, setIsDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!analysisId) return;

    const es = new EventSource(`${API_URL}/analyze/progress/${analysisId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: ProgressEvent = JSON.parse(e.data);
        if (event.heartbeat) return;

        setSteps((prev) => {
          const exists = prev.some((s) => s.index === event.index);
          if (exists) return prev;
          return [...prev, event];
        });

        if (event.done) {
          setIsDone(true);
          es.close();
          if (event.error) {
            onError(event.error);
          } else {
            onComplete();
          }
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      es.close();
      if (!isDone) {
        onError("Connection lost. Please refresh.");
      }
    };

    return () => {
      es.close();
    };
  }, [analysisId]); // eslint-disable-line react-hooks/exhaustive-deps

  return { steps, isDone };
}
