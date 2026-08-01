// Mirrors backend/app/analyzer/models.py + the JSON shape returned by
// POST /analyze in backend/app/main.py. Keep these in sync manually --
// there are only ~6 shapes and a shared schema package would be overkill
// for a v1.

export type NodeType =
  | "file"
  | "component"
  | "function"
  | "class"
  | "api_endpoint"
  | "db_model"
  | "service";

export type EdgeType = "imports" | "calls" | "defines";

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  file: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: EdgeType;
}

export interface ApiRouteInfo {
  method: string;
  path: string;
  handler: string;
  line: number;
}

export interface ImportRef {
  module: string;
  names: string[];
  is_relative: boolean;
  line: number;
}

export interface FunctionInfo {
  name: string;
  line: number;
  is_async: boolean;
  decorators: string[];
}

export interface ClassInfo {
  name: string;
  line: number;
  bases: string[];
  is_react_component: boolean;
}

export interface FileAnalysis {
  path: string;
  language: string;
  loc: number;
  imports: ImportRef[];
  functions: FunctionInfo[];
  classes: ClassInfo[];
  api_routes: ApiRouteInfo[];
  is_react_component_file: boolean;
  is_db_model_file: boolean;
  parse_error: string | null;
  source_snippet: string | null;
}

export interface RepoOverview {
  total_files: number;
  total_components: number;
  total_api_endpoints: number;
  total_db_models: number;
  language_breakdown: Record<string, number>;
}

export interface AnalyzeResponse {
  repo_name: string;
  overview: RepoOverview;
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  files: FileAnalysis[];
}
