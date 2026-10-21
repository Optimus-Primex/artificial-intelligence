# Artificial Intelligence

[![CI](https://github.com/Optimus-Primex/artificial-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/Optimus-Primex/artificial-intelligence/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Coverage: 90%+](https://img.shields.io/badge/coverage-90%25%2B-brightgreen)](#)

AI toolkit for the **Stellar / Soroban** ecosystem.

This repository is a monorepo with two parts:

- **`python/`** — `stellar-ai`, a FastAPI service and agent core that reads
  Stellar Horizon and Soroban RPC data and produces LLM-powered analysis.
- **`typescript/`** — `@optimus-primex/ai-client`, a typed client/SDK for the
  service.

> Status: early framework with a working end-to-end path. The service, clients,
> analyzers and SDK are in place. Two providers ship: a deterministic offline
> `static` stub (used by tests/CI) and an `openai` provider for any
> OpenAI-compatible `/chat/completions` endpoint.

## Why

Stellar exposes a lot of machine data (ledgers, accounts, assets, Soroban
contract events). This project is the home for AI features on top of it:
summarising network health, decoding contract events and answering
natural-language questions today; anomaly detection is the next milestone
(see [`docs/roadmap.md`](docs/roadmap.md)).

## Layout

```
artificial-intelligence/
├── python/
│   ├── src/stellar_ai/
│   │   ├── app.py            # FastAPI application + routes
│   │   ├── config.py         # settings (pydantic-settings)
│   │   ├── schemas.py        # request/response models
│   │   ├── analyzers.py      # pure analysis helpers (network + events)
│   │   ├── agents/           # agent interface + Stellar insight agent
│   │   ├── llm/              # pluggable LLM providers (stub included)
│   │   └── stellar/          # Horizon + Soroban RPC clients, XDR decoding
│   └── tests/
├── typescript/
│   ├── src/                  # client SDK
│   └── test/
└── docs/
```

## Quick start — Python

```bash
cd python
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn stellar_ai.app:app --reload   # http://127.0.0.1:8000
pytest                                 # run the tests
ruff check . && ruff format --check .
```

Interactive API docs are at `http://127.0.0.1:8000/docs`.

## Quick start — TypeScript

```bash
cd typescript
npm install
npm run build
npm test
```

```ts
import { AiClient } from "@optimus-primex/ai-client";

const client = new AiClient("http://127.0.0.1:8000");
const health = await client.health();
const status = await client.networkStatus("testnet");
```

## Endpoints (v1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | no | Liveness probe. |
| `GET` | `/ready` | no | Readiness probe (checks Horizon + RPC). |
| `GET` | `/api/v1/network/status?network=testnet` | yes | Latest ledger / node health. |
| `GET` | `/api/v1/contracts/{contract_id}/events?start_ledger=...&limit=...` | yes | Decode and summarise Soroban contract events. |
| `POST` | `/api/v1/analyze` | yes | Recompute metrics and return a grounded summary. |
| `POST` | `/api/v1/chat` | yes | Natural-language query through an agent. |

Every response carries an `X-Request-ID`; errors use a consistent envelope
(see [`docs/errors.md`](docs/errors.md)).

### Soroban contract events

`GET /api/v1/contracts/{contract_id}/events` calls Soroban RPC `getEvents` and
decodes the base64 XDR `topic`/`value` fields with the official `stellar-sdk`.
The response includes the event name (first topic), contract id, ledger, tx
hash, decoded topics/value, and the raw event as a fallback when a payload
cannot be decoded. `limit` is capped at 200; invalid contract ids or ledger
parameters return `400`, RPC failures return `502`.

`POST /api/v1/chat` accepts optional `contract_id` and `start_ledger` fields; when
supplied, the decoded event summary is added to the prompt as context. Existing
network-only chat requests are unchanged.

Verified against the testnet escrow `CBBWLHEI3HUBZOVHCKSYGARLRGZYQ4VZCHYBYAIQN2A727J3COI7LMOQ`:
the decoder read `created`, `funded` and `released` events with zero decode failures.

## Configuration

Settings are environment variables with the `STELLAR_AI_` prefix (see
[`.env.example`](.env.example)): network, LLM provider + credentials,
`STELLAR_AI_API_KEYS` (bearer keys; empty disables auth),
`STELLAR_AI_CORS_ORIGINS`, and `STELLAR_AI_LOG_FORMAT` (`text` or `json`).

### Using a real model

```bash
export STELLAR_AI_LLM_PROVIDER=openai
export STELLAR_AI_LLM_API_KEY=sk-...
export STELLAR_AI_LLM_MODEL=gpt-4o-mini
# Optional: point at a local OpenAI-compatible gateway (vLLM, Ollama, ...)
export STELLAR_AI_LLM_BASE_URL=http://127.0.0.1:11434/v1
```

The provider calls `POST {base_url}/chat/completions` with the grounded prompt.
Missing keys, HTTP failures and malformed completions surface as a `502` with a
clear message; keys are never logged.

## Docker

```bash
docker compose up --build     # http://localhost:8000
```

## License

MIT © 2026 Optimus-Primex
