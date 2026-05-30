"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { startAnalysis } from "@/lib/api";
import { detectPlatform } from "@/lib/utils";

function PlatformIcon({ url }: { url: string }) {
  const platform = detectPlatform(url);
  if (platform === "youtube") {
    return (
      <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 24 24">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    );
  }
  if (platform === "instagram") {
    return (
      <svg className="h-5 w-5 text-pink-400" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    );
  }
  return <span className="h-5 w-5 text-muted-foreground opacity-40">🔗</span>;
}

export function AnalyzeForm() {
  const router = useRouter();
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlA.trim() || !urlB.trim()) {
      setError("Please enter both video URLs.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const { analysis_id } = await startAnalysis(urlA.trim(), urlB.trim());
      router.push(`/analysis/${analysis_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start analysis.";
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto space-y-4">
      <div className="space-y-3">
        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <PlatformIcon url={urlA} />
          </div>
          <Input
            value={urlA}
            onChange={(e) => setUrlA(e.target.value)}
            placeholder="Video A — YouTube Short URL"
            className="pl-10 h-12 bg-muted/30 border-border/50 focus:border-primary/50 transition-colors"
            disabled={loading}
          />
        </div>

        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <PlatformIcon url={urlB} />
          </div>
          <Input
            value={urlB}
            onChange={(e) => setUrlB(e.target.value)}
            placeholder="Video B — Instagram Reel URL"
            className="pl-10 h-12 bg-muted/30 border-border/50 focus:border-primary/50 transition-colors"
            disabled={loading}
          />
        </div>
      </div>

      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}

      <Button
        type="submit"
        size="lg"
        className="w-full h-12 font-semibold text-base transition-all"
        disabled={loading || !urlA.trim() || !urlB.trim()}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Starting Analysis...
          </span>
        ) : (
          "Analyze Both Videos →"
        )}
      </Button>
    </form>
  );
}
