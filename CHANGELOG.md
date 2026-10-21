# Changelog

All notable changes to this project are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-21

### Added

- FastAPI service with `/health`, `/ready`, `/api/v1/network/status`,
  `/api/v1/analyze` and `/api/v1/chat`.
- `OpenAICompatibleProvider` for any `/chat/completions` endpoint, configured
  with `STELLAR_AI_LLM_*`; the deterministic `static` provider remains the
  default for CI and offline development.
- Soroban `getEvents` support, base64 SCVal decoding with the official
  `stellar-sdk`, event metrics and `GET /api/v1/contracts/{id}/events`.
- Optional contract-event context for chat, grounded in decoded events.
- TypeScript SDK with bearer-key support and safe non-JSON error handling.
- 82 tests at 96% coverage, including real offline XDR fixtures.

### Fixed

- Invalid Horizon JSON now raises `StellarClientError` instead of a 500.
- Missing/unknown Soroban health is treated as unhealthy.
- Protocol version is read from `getLatestLedger`, not `getHealth`.

### Documentation

- Real-model setup, the events endpoint, event schemas, architecture and
  roadmap updates.
