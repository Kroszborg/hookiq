"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ProgressEvent } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

export function useProgress(
  analysisId: string | null,
  onComplete: () => void,
  onError: (error: string) => void
) {
  const [steps, setSteps] = useState<ProgressEvent[]>([]);
  const [isDone, setIsDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const isDoneRef = useRef(false);

  const connect = useCallback(() => {
    if (!analysisId || isDoneRef.current) return;

    const es = new EventSource(`${API_URL}/analyze/progress/${analysisId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: ProgressEvent = JSON.parse(e.data);
        if (event.heartbeat) return;

        retriesRef.current = 0; // Reset retries on successful message

        setSteps((prev) => {
          if (prev.some((s) => s.index === event.index)) return prev;
          return [...prev, event];
        });

        if (event.done) {
          isDoneRef.current = true;
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
      if (isDoneRef.current) return;

      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current += 1;
        setTimeout(connect, RETRY_DELAY_MS * retriesRef.current);
      } else {
        onError("Connection lost after retries. Please refresh.");
      }
    };
  }, [analysisId, onComplete, onError]);

  useEffect(() => {
    if (!analysisId) return;
    isDoneRef.current = false;
    retriesRef.current = 0;
    connect();
    return () => {
      esRef.current?.close();
    };
  }, [analysisId, connect]);

  return { steps, isDone };
}
