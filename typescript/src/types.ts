/** Shared types mirroring the Python service's API models. */

export interface NetworkStatus {
  network: string;
  healthy: boolean;
  latest_ledger?: number | null;
  ledger_lag_seconds?: number | null;
  protocol_version?: number | null;
  rpc_health?: string | null;
  horizon_url?: string | null;
  rpc_url?: string | null;
}

export interface AnalyzeRequest {
  network?: string;
}

export interface AnalyzeResponse {
  summary: string;
  metrics: NetworkStatus;
  provider: string;
}

export interface ChatRequest {
  message: string;
  network?: string;
}

export interface ChatResponse {
  answer: string;
  metrics: NetworkStatus;
  provider: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  provider: string;
}

export interface ClientOptions {
  /** Custom fetch implementation (defaults to `globalThis.fetch`). */
  fetch?: typeof fetch;
}
