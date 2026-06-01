export interface VideoCard {
  id: string;
  platform: string; // "youtube" | "instagram" | "tiktok"
  url: string;
  title: string | null;
  creator: string | null;
  followers: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  engagement_rate: number | null;
  duration: number | null;
  upload_date: string | null;
  hashtags: string[];
  thumbnail_url: string | null;
  transcript?: string | null;
}

export interface HookAnalysis {
  curiosity_score: number;
  emotional_score: number;
  clarity_score: number;
  retention_potential: number;
  summary: string;
}

export interface StructureSegment {
  segment: string;  // "Hook" | "Story" | "Value" | "CTA" or lowercase variants
  start_time: number;
  end_time: number;
  summary: string;
}

export interface ViralPattern {
  present: boolean;
  score: number;
  evidence: string;
}

export interface ViralPatterns {
  curiosity_gap: ViralPattern;
  open_loop: ViralPattern;
  social_proof: ViralPattern;
  authority: ViralPattern;
  urgency: ViralPattern;
  novelty: ViralPattern;
}

export interface Recommendation {
  rank: number;
  title: string;
  action: string;
  evidence_from_a: string;
}

export interface ComparisonInsights {
  winner: "A" | "B" | "tie";
  performance_delta_pct: number;
  hook_comparison: string;
  content_comparison: string;
  summary: string;
}

export interface Analysis {
  id: string;
  status: "processing" | "complete" | "failed";
  video_a: VideoCard | null;
  video_b: VideoCard | null;
  hook_analysis_a: HookAnalysis | null;
  hook_analysis_b: HookAnalysis | null;
  structure_a: StructureSegment[] | null;
  structure_b: StructureSegment[] | null;
  viral_patterns_a: ViralPatterns | null;
  viral_patterns_b: ViralPatterns | null;
  recommendations: Recommendation[] | null;
  comparison_insights: ComparisonInsights | null;
  error_message?: string | null;
}

export interface ProgressEvent {
  step: string;
  index: number;
  total: number;
  done: boolean;
  error?: string | null;
  heartbeat?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

export interface Citation {
  tag: string;
  label: "A" | "B";
  chunk_id: number;
  score: number;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  status: string;
  video_a_thumbnail: string | null;
  video_a_creator: string | null;
  video_b_thumbnail: string | null;
  video_b_creator: string | null;
}
