export interface QueryResponse {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
}

export interface DagsterAsset {
  key: string;
  description: string | null;
  jobs: string[];
}

export interface MaterializeResponse {
  run_id: string;
  status: string;
}

export interface RunStatus {
  run_id: string;
  status: string;
  started_at: number | null;
  ended_at: number | null;
}

export interface ChatResponse {
  reply: string;
  model: string;
}

export interface ChatModel {
  id: string;
  name: string;
}

export interface SearchResult {
  score: number;
  payload: Record<string, unknown>;
}

export interface ServiceStatus {
  key: string;
  name: string;
  category: string;
  external_url: string;
  status: "ok" | "error";
}

export interface ColumnInfo {
  name: string;
  type: string;
}

export type TableList = Record<string, string[]>;
