import { describe, expect, it, vi } from "vitest";

import { AiClient, AiClientError } from "../src/index.js";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function clientWith(fetchImpl: typeof fetch): AiClient {
  return new AiClient("http://localhost:8000/", { fetch: fetchImpl });
}

describe("AiClient", () => {
  it("strips trailing slashes from the base URL", () => {
    const client = clientWith(vi.fn() as unknown as typeof fetch);
    expect(client.baseUrl).toBe("http://localhost:8000");
  });

  it("GETs /health", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ status: "ok", app: "stellar-ai", provider: "static" }),
    );
    const client = clientWith(fetchMock as unknown as typeof fetch);

    const health = await client.health();

    expect(health.status).toBe("ok");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/health");
  });

  it("builds the network query string", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ network: "testnet", healthy: true }),
    );
    const client = clientWith(fetchMock as unknown as typeof fetch);

    const status = await client.networkStatus("testnet");

    expect(status.network).toBe("testnet");
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "http://localhost:8000/api/v1/network/status?network=testnet",
    );
  });

  it("POSTs chat requests as JSON", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({
        answer: "yes",
        metrics: { network: "testnet", healthy: true },
        provider: "static",
      }),
    );
    const client = clientWith(fetchMock as unknown as typeof fetch);

    const reply = await client.chat({ message: "hello", network: "testnet" });

    expect(reply.answer).toBe("yes");
    const call = fetchMock.mock.calls[0];
    expect(call?.[0]).toBe("http://localhost:8000/api/v1/chat");
    expect(call?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      message: "hello",
      network: "testnet",
    });
  });

  it("throws AiClientError on a non-2xx response", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ detail: "rpc unreachable" }, 502),
    );
    const client = clientWith(fetchMock as unknown as typeof fetch);

    await expect(client.networkStatus("testnet")).rejects.toBeInstanceOf(AiClientError);
  });
});
