import axios from "axios";
import type { AnalyzeResponse } from "./types";

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts),
// so this works unchanged whether the backend runs locally or is deployed
// behind the same origin in production.
const client = axios.create({ baseURL: "/api" });

export async function analyzeRepo(repoUrl: string): Promise<AnalyzeResponse> {
  const { data } = await client.post<AnalyzeResponse>("/analyze", {
    repo_url: repoUrl,
  });
  return data;
}
