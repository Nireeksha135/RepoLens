import axios from "axios";
import type { GraphEdge, GraphNode } from "./types";

export interface ImpactedNode {
  id: string;
  label: string;
  node_type: string;
  hops: number;
  severity: "HIGH" | "MEDIUM" | "LOW";
  path: string[];
}

export interface ImpactResponse {
  target: string;
  high: ImpactedNode[];
  medium: ImpactedNode[];
  low: ImpactedNode[];
}

const client = axios.create({ baseURL: "/api" });

export async function analyzeImpact(
  nodes: GraphNode[],
  edges: GraphEdge[],
  target: string
): Promise<ImpactResponse> {
  const { data } = await client.post<ImpactResponse>("/impact", { nodes, edges, target });
  return data;
}
