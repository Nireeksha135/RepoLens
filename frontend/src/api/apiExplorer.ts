import axios from "axios";
import type { GraphEdge, GraphNode } from "./types";

export interface ApiRouteSummary {
  method: string;
  path: string;
  route_id: string;
  defined_in: string | null;
  controller: string | null;
  uses: string[];
  database_models: string[];
  called_by: string[];
}

const client = axios.create({ baseURL: "/api" });

export async function fetchApiRoutes(
  nodes: GraphNode[],
  edges: GraphEdge[],
  handlers: Record<string, string>
): Promise<ApiRouteSummary[]> {
  const { data } = await client.post<ApiRouteSummary[]>("/api-routes", { nodes, edges, handlers });
  return data;
}
