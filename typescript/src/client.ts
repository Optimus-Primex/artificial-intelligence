import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ChatRequest,
  ChatResponse,
  ClientOptions,
  HealthResponse,
  NetworkStatus,
} from "./types.js";

/** Raised when the service returns a non-2xx response. */
export class AiClientError extends Error {
  readonly status: number;
  readonly path: string;
  readonly body: unknown;

  constructor(status: number, path: string, body: unknown) {
    super(`Stellar AI request to ${path} failed with status ${status}`);
    this.name = "AiClientError";
    this.status = status;
    this.path = path;
    this.body = body;
  }
}

/** Thin, typed client for the Stellar AI service. */
export class AiClient {
  readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(baseUrl = "http://127.0.0.1:8000", options: ClientOptions = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    const impl = options.fetch ?? globalThis.fetch;
    if (typeof impl !== "function") {
      throw new Error("No fetch implementation available; pass `{ fetch }` to AiClient.");
    }
    this.fetchImpl = impl;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, init);
    const text = await response.text();
    const data: unknown = text ? JSON.parse(text) : undefined;
    if (!response.ok) {
      throw new AiClientError(response.status, path, data);
    }
    return data as T;
  }

  health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  networkStatus(network?: string): Promise<NetworkStatus> {
    const query = network ? `?network=${encodeURIComponent(network)}` : "";
    return this.request<NetworkStatus>(`/api/v1/network/status${query}`);
  }

  analyze(request: AnalyzeRequest = {}): Promise<AnalyzeResponse> {
    return this.request<AnalyzeResponse>("/api/v1/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  chat(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
  }
}
