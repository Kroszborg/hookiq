import axios from "axios";
import type { Analysis, HistoryItem } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
});

export async function startAnalysis(videoAUrl: string, videoBUrl: string): Promise<{ analysis_id: string }> {
  const { data } = await api.post("/analyze", {
    video_a_url: videoAUrl,
    video_b_url: videoBUrl,
  });
  return data;
}

export async function getAnalysis(id: string): Promise<Analysis> {
  const { data } = await api.get(`/analyze/${id}`);
  return data;
}

export async function getHistory(limit = 20): Promise<HistoryItem[]> {
  const { data } = await api.get(`/history?limit=${limit}`);
  return data;
}

export function getApiUrl(): string {
  return API_URL;
}
