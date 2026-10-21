# Architecture

```
            ┌───────────────────────────────────────────────┐
  HTTP ───▶ │  FastAPI service (stellar_ai.app)             │
            │    /health  /api/v1/network  /analyze  /chat  │
            └───────────────┬───────────────────────────────┘
                            │
             ┌──────────────┼───────────────────────┐
             ▼              ▼                       ▼
        ┌─────────┐   ┌──────────────┐        ┌────────────┐
        │ agents  │──▶│  analyzers   │        │  stellar/  │
        │         │   │ (pure logic) │        │  clients   │
        └────┬────┘   └──────────────┘        └─────┬──────┘
             │                                      │
             ▼                                      ▼
        ┌─────────┐                       Horizon REST / Soroban RPC
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
- **Pluggable models.** `llm/` defines a `LLMProvider` protocol. The default
  `StaticProvider` is deterministic (great for tests/CI); `OpenAICompatibleProvider`
  calls any `/chat/completions` endpoint and is configured through
  `STELLAR_AI_LLM_*`. New providers can be added without touching agents or
  routes.

## Data flow (example: `/api/v1/chat`)

1. The route resolves the configured agent.
2. The agent fetches current network data through `stellar/` clients.
3. `analyzers` derives metrics (ledger lag, health summary, ...).
4. The `LLMProvider` turns the metrics + question into a natural-language
   answer.
5. The route returns the answer plus the structured metrics.

## TypeScript client

`@optimus-primex/ai-client` mirrors the HTTP API with typed request/response
models and a thin `fetch`-based client.
