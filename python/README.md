# stellar-ai (Python)

FastAPI service and agent core for the [Artificial Intelligence](../README.md)
monorepo. Reads Stellar Horizon and Soroban RPC data and produces LLM-powered
analysis.

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn stellar_ai.app:app --reload   # http://127.0.0.1:8000/docs
```

## Test / lint

```bash
pytest
ruff check . && ruff format --check .
```

## Configuration

Environment variables use the `STELLAR_AI_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `STELLAR_AI_DEFAULT_NETWORK` | `testnet` | Network used when none is given. |
| `STELLAR_AI_LLM_PROVIDER` | `static` | LLM provider (`static` ships built in). |
| `STELLAR_AI_HORIZON_URL` | per-network | Override the Horizon endpoint. |
| `STELLAR_AI_SOROBAN_RPC_URL` | per-network | Override the Soroban RPC endpoint. |
| `STELLAR_AI_REQUEST_TIMEOUT` | `10` | Outbound request timeout (seconds). |
