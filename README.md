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

> Status: early framework. The service, clients, analyzers and SDK are in
> place; model providers are pluggable and ship with a deterministic stub so
> the whole stack runs and tests without network access or API keys.

## Why

Stellar exposes a lot of machine data (ledgers, accounts, assets, Soroban
contract events). This project is the home for AI features on top of it:
summarising network health, explaining contract activity, answering
natural-language questions, and flagging anomalies.

## Layout

```
artificial-intelligence/
├── python/
│   ├── src/stellar_ai/
│   │   ├── app.py            # FastAPI application + routes
│   │   ├── config.py         # settings (pydantic-settings)
│   │   ├── schemas.py        # request/response models
│   │   ├── analyzers.py      # pure analysis helpers
│   │   ├── agents/           # agent interface + Stellar insight agent
│   │   ├── llm/              # pluggable LLM providers (stub included)
│   │   └── stellar/          # Horizon + Soroban RPC clients
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
| `POST` | `/api/v1/analyze` | yes | Analyse supplied network data. |
| `POST` | `/api/v1/chat` | yes | Natural-language query through an agent. |

Every response carries an `X-Request-ID`; errors use a consistent envelope
(see [`docs/errors.md`](docs/errors.md)).

## Configuration

Settings are environment variables with the `STELLAR_AI_` prefix (see
[`.env.example`](.env.example)): network, LLM provider, `STELLAR_AI_API_KEYS`
(bearer keys; empty disables auth), `STELLAR_AI_CORS_ORIGINS`, and
`STELLAR_AI_LOG_FORMAT` (`text` or `json`).

## Docker

```bash
docker compose up --build     # http://localhost:8000
```

## License

MIT © 2026 Optimus-Primex
