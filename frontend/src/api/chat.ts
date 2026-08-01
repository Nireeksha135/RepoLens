import axios from "axios";
import type { FileAnalysis } from "./types";

export interface ChatResponse {
  answer: string;
  sources: string[];
}

const client = axios.create({ baseURL: "/api" });

export async function askRepoLens(files: FileAnalysis[], question: string): Promise<ChatResponse> {
  const { data } = await client.post<ChatResponse>("/chat", { files, question });
  return data;
}
