import axios from "axios";
import { API_BASE_URL } from "./config";
import type { AnalyzeResponse } from "./types";

const client = axios.create({ baseURL: API_BASE_URL });

export async function analyzeRepo(repoUrl: string): Promise<AnalyzeResponse> {
  const { data } = await client.post<AnalyzeResponse>("/analyze", {
    repo_url: repoUrl,
  });
  return data;
}
