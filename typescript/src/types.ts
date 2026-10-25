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
  /** Asset to scan for whale transfers: `XLM` or `CODE:ISSUER`. */
  asset?: string;
  /** Override the configured whale threshold for this request. */
  whale_threshold?: number;
  /** Number of recent payments to inspect (1-200). */
  payment_limit?: number;
}

export interface WhaleAlert {
  amount: number;
  asset: string;
  from_account?: string | null;
  to_account?: string | null;
  transaction_hash?: string | null;
  created_at?: string | null;
  ledger?: number | null;
}

export interface PaymentAnalysis {
  network: string;
  asset: string;
  threshold: number;
  limit: number;
  payments_scanned: number;
  matching_payments: number;
  skipped_payments?: number;
  whale_count: number;
  total_volume: number;
  largest_payment?: WhaleAlert | null;
  alerts: WhaleAlert[];
}

export interface AnalyzeResponse {
  summary: string;
  metrics: NetworkStatus;
  provider: string;
  payments?: PaymentAnalysis | null;
  alerts?: WhaleAlert[];
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
  /** Sent as `Authorization: Bearer <apiKey>` when the service requires auth. */
  apiKey?: string;
}
