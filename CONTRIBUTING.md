# Contributing

Thanks for your interest in **Artificial Intelligence** — an AI toolkit for the
Stellar/Soroban ecosystem. This is a monorepo with a Python service (`python/`)
and a TypeScript SDK (`typescript/`).

## Development setup

### Python

```bash
cd python
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest --cov=stellar_ai
ruff check . && ruff format --check .
```

### TypeScript

```bash
cd typescript
npm install
npm run lint     # typecheck
npm run build
npm test
```

## Making a change

1. Pick or open an issue. Labels use `area: *` and `complexity: *`.
2. Create a branch: `git checkout -b fix/short-description`.
3. Keep changes focused; add tests for new behaviour.
4. Make sure Python tests, `ruff`, and the TypeScript build/tests pass.
5. Open a pull request describing the change and linking the issue.

## Style

- Python: `ruff` (line length 100). Type hints on public functions.
- TypeScript: strict mode; keep the public API typed and documented.
- No hardcoded secrets. New settings go through `stellar_ai/config.py`
  (`STELLAR_AI_*` env vars) and `.env.example`.

## Reporting bugs / security issues

Open a GitHub issue for bugs. For security problems, follow
[`SECURITY.md`](SECURITY.md) instead of opening a public issue.
