# Roadmap

## Phase 1 — Framework (this milestone)
- [x] Monorepo layout (Python service + TypeScript SDK)
- [x] FastAPI service with `/health`, `/network/status`, `/analyze`, `/chat`
- [x] Horizon and Soroban RPC clients
- [x] Pluggable LLM provider with a deterministic stub
- [x] Tests + CI (Python 3.11/3.12, TypeScript)

## Phase 2 — Real model providers
- [x] OpenAI-compatible HTTP provider (works with OpenAI and local gateways)
- [ ] Native Anthropic provider
- [ ] Prompt templates + streaming responses
- [ ] Token/cost accounting

## Phase 3 — Deeper Stellar/Soroban intelligence
- [ ] Soroban contract event summarisation and anomaly detection
- [ ] Account/asset activity digests
- [ ] Retrieval over historical ledger/event data

## Phase 4 — Product surface
- [ ] Auth + rate limiting
- [ ] Web dashboard
- [ ] Published SDK (`@optimus-primex/ai-client`) and container image
