# Architecture

```
            ┌────────────────────────────────────────────────────────┐
  HTTP ───▶ │  FastAPI service (stellar_ai.app)                       │
            │    /health  /network  /contracts/{id}/events  /chat     │
            └───────────────┬────────────────────────────────────────┘
                            │
             ┌──────────────┼───────────────────────┐
             ▼              ▼                       ▼
        ┌─────────┐   ┌──────────────┐        ┌────────────┐
        │ agents  │──▶│  analyzers   │        │  stellar/  │
        │         │   │ (pure logic) │        │  clients   │
        └────┬────┘   └──────────────┘        └─────┬──────┘
             │                                      │
             ▼                                      ▼
        ┌─────────┐                Horizon REST / Soroban RPC + XDR
        │  llm/   │  (pluggable provider; deterministic stub by default)
        └─────────┘
```

## Principles

- **Dependency injection by default.** The FastAPI app builds its collaborators
  (Stellar clients, LLM provider) in one place and hands them to routes via a
  small container, so tests can swap in fakes and no test touches the network.
- **Pure analysis separate from I/O.** `analyzers.py` contains deterministic
  functions over plain data; the agents combine them with fetched data + LLM
  output.
- **Defensive XDR decoding.** `stellar/events.py` uses the official
  `stellar-sdk` `ScVal` helpers to decode Soroban event topics/values. A bad
  payload keeps its raw base64 and records a decode error instead of failing
  the request, so partially malformed event windows remain inspectable.
- **Pluggable models.** `llm/` defines a `LLMProvider` protocol. The default
  `StaticProvider` is deterministic (great for tests/CI); `OpenAICompatibleProvider`
  calls any `/chat/completions` endpoint and is configured through
  `STELLAR_AI_LLM_*`. New providers can be added without touching agents or
  routes.

## Data flow (example: `/api/v1/chat`)

1. The route resolves the configured agent.
2. The agent fetches current network data through `stellar/` clients.
3. If a `contract_id` is supplied, `SorobanRpcClient.get_events` calls
   `getEvents`, `stellar/events.py` decodes the XDR, and `analyzers` derives
   event metrics plus a factual summary.
4. `analyzers` derives network metrics (ledger lag, health summary, ...).
5. The `LLMProvider` turns the grounded context + question into a
   natural-language answer.
6. The route returns the answer plus the structured network metrics.

## Contract events flow (`/api/v1/contracts/{contract_id}/events`)

1. The route validates the contract id, `start_ledger` and `limit` (`400` on
   bad input).
2. `SorobanRpcClient.get_events` sends `{startLedger, filters, limit,
   xdrFormat}` to Soroban RPC (`502` on RPC failure).
3. `stellar/events.py` decodes each event's `topic`/`value` XDR and preserves
   raw fallbacks for malformed payloads.
4. `analyzers.build_event_metrics` counts events by name/contract, computes
   ledger statistics and failed decodes; `summarise_events` renders a short
   factual summary.
5. The route returns `{contract_id, start_ledger, latest_ledger, summary,
   events}`.

## TypeScript client

`@optimus-primex/ai-client` mirrors the HTTP API with typed request/response
models and a thin `fetch`-based client.
