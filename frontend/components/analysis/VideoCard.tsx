"use client";

import { useState } from "react";
import { cn, engagementBg, formatDuration, formatNumber } from "@/lib/utils";
import type { VideoCard as VideoCardType, HookAnalysis, ViralPatterns, StructureSegment } from "@/types";
import { ViralScore } from "./ViralScore";
import { TranscriptViewer } from "./TranscriptViewer";

interface Props {
  video: VideoCardType;
  label: "A" | "B";
  hook?: HookAnalysis | null;
  patterns?: ViralPatterns | null;
  structure?: StructureSegment[] | null;
  transcript?: string | null;
}

function PlatformBadge({ platform }: { platform: string }) {
  const styles: Record<string, string> = {
    youtube: "text-red-400/80 border-red-400/20 bg-red-400/5",
    instagram: "text-pink-400/80 border-pink-400/20 bg-pink-400/5",
    tiktok: "text-cyan-400/80 border-cyan-400/20 bg-cyan-400/5",
  };
  const labels: Record<string, string> = {
    youtube: "YouTube", instagram: "Instagram", tiktok: "TikTok"
  };
  return (
    <span className={cn("font-mono text-[9px] tracking-widest uppercase px-2 py-0.5 rounded border", styles[platform] ?? styles.youtube)}>
      {labels[platform] ?? platform}
    </span>
  );
}

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === "instagram") return (
    <svg className="h-8 w-8 text-pink-400/30" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
    </svg>
  );
  if (platform === "tiktok") return (
    <svg className="h-8 w-8 text-cyan-400/30" fill="currentColor" viewBox="0 0 24 24">
      <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.28 8.28 0 004.84 1.56V6.79a4.85 4.85 0 01-1.07-.1z"/>
    </svg>
  );
  return (
    <svg className="h-8 w-8 text-red-400/30" fill="currentColor" viewBox="0 0 24 24">
      <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-0.5">
      <p className="font-mono text-[10px] text-muted-foreground/50 tracking-widest uppercase">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function VideoCard({ video, label, hook, patterns, structure, transcript }: Props) {
  const [imgFailed, setImgFailed] = useState(false);
  const hasViews = video.views !== null && video.views !== undefined;
  const rawEngagement = (video.likes ?? 0) + (video.comments ?? 0);
  const showThumbnail = video.thumbnail_url && !imgFailed;

  return (
    <div className="bg-white/[0.02] border border-border/40 rounded-xl overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-white/[0.03]">
        {showThumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url!}
            alt=""
            className="w-full h-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <PlatformIcon platform={video.platform} />
            <span className="font-mono text-[9px] text-muted-foreground/30 uppercase tracking-widest">
              {video.platform} · no preview
            </span>
          </div>
        )}

        <div className="absolute top-2.5 left-2.5">
          <span className="bg-background/90 font-mono text-[9px] tracking-widest uppercase px-2 py-0.5 rounded border border-border/40">
            Video {label}
          </span>
        </div>
        <div className="absolute top-2.5 right-2.5">
          <PlatformBadge platform={video.platform} />
        </div>
        {video.duration != null && (
          <div className="absolute bottom-2 right-2 bg-background/90 font-mono text-[10px] px-1.5 py-0.5 rounded">
            {formatDuration(video.duration)}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {video.title && (
          <p className="text-sm font-medium leading-snug line-clamp-2">{video.title}</p>
        )}

        {/* Creator + Viral Score */}
        <div className="flex items-start justify-between gap-3">
          {video.creator && (
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="h-7 w-7 rounded-full bg-white/[0.06] border border-border/40 flex items-center justify-center text-xs font-bold shrink-0">
                {video.creator.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{video.creator}</p>
                {video.followers != null && (
                  <p className="text-xs text-muted-foreground font-mono">{formatNumber(video.followers)} followers</p>
                )}
              </div>
            </div>
          )}
          <ViralScore video={video} hook={hook ?? null} patterns={patterns ?? null} label={label} />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 pt-1">
          <Stat label="Views" value={formatNumber(video.views)} />
          <Stat label="Likes" value={formatNumber(video.likes)} />
          <Stat label="Comments" value={formatNumber(video.comments)} />
        </div>

        {/* Engagement rate */}
        <div className={cn("rounded-lg border px-3 py-2.5 text-center", engagementBg(video.engagement_rate))}>
          {hasViews && video.engagement_rate != null ? (
            <>
              <span className="font-mono text-base font-bold tabular-nums">
                {video.engagement_rate.toFixed(2)}%
              </span>
              <span className="text-xs ml-1.5 opacity-70">engagement rate</span>
            </>
          ) : video.engagement_rate != null ? (
            <>
              <span className="font-mono text-base font-bold tabular-nums">
                {video.engagement_rate.toFixed(2)}%
              </span>
              <span className="text-xs ml-1.5 opacity-70">follower ER</span>
            </>
          ) : (
            <div>
              <span className="font-mono text-base font-bold tabular-nums text-muted-foreground">—</span>
              <span className="text-xs ml-1.5 opacity-70">no view data</span>
              {rawEngagement > 0 && (
                <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                  {formatNumber(rawEngagement)} raw interactions
                </p>
              )}
            </div>
          )}
        </div>

        {/* Meta */}
        <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
          {video.upload_date && <span>{video.upload_date}</span>}
          {video.hashtags.length > 0 && (
            <span className="truncate ml-2">#{video.hashtags.slice(0, 3).join(" #")}</span>
          )}
        </div>

        {/* Transcript viewer */}
        <TranscriptViewer
          transcript={transcript ?? null}
          transcriptSegments={video.transcript_segments}
          structureSegments={structure ?? []}
          label={label}
        />
      </div>
    </div>
  );
}
