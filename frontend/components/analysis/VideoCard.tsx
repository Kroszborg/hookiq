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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-0.5">
      <p className="font-mono text-[10px] text-muted-foreground/50 tracking-widest uppercase">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function VideoCard({ video, label, hook, patterns, structure, transcript }: Props) {
  const hasViews = video.views !== null && video.views !== undefined;
  const rawEngagement = (video.likes ?? 0) + (video.comments ?? 0);

  return (
    <div className="bg-white/[0.02] border border-border/40 rounded-xl overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-white/[0.03]">
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg className="h-8 w-8 text-white/10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        )}
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
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
        {/* Title */}
        {video.title && (
          <p className="text-sm font-medium leading-snug line-clamp-2">{video.title}</p>
        )}

        {/* Creator + Viral Score row */}
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
