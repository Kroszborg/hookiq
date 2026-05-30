import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "N/A";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "N/A";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function engagementColor(rate: number | null | undefined): string {
  if (rate == null) return "text-muted-foreground";
  if (rate >= 5) return "text-emerald-400";
  if (rate >= 2) return "text-yellow-400";
  return "text-red-400";
}

export function engagementBg(rate: number | null | undefined): string {
  if (rate == null) return "bg-muted/40 text-muted-foreground";
  if (rate >= 5) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  if (rate >= 2) return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
  return "bg-red-500/10 text-red-400 border-red-500/30";
}

export function platformColor(platform: string): { bg: string; text: string } {
  if (platform === "youtube") return { bg: "bg-red-500/10 border-red-500/30", text: "text-red-400" };
  return { bg: "bg-pink-500/10 border-pink-500/30", text: "text-pink-400" };
}

export function detectPlatform(url: string): "youtube" | "instagram" | "unknown" {
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
  if (url.includes("instagram.com")) return "instagram";
  return "unknown";
}
