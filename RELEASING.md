# Releasing

This repository ships two packages:

- `@optimus-primex/ai-client` (TypeScript SDK)
- `stellar-ai` (Python service)

Both use Semantic Versioning. Update `CHANGELOG.md` and the package version
before tagging.

## 1. Prepare

```bash
# TypeScript
cd typescript
npm ci
npm test
npm run build
npm pack --dry-run   # inspect the published file list

# Python
cd ../python
python -m pip install -e ".[dev,release]"
python -m pytest --cov=stellar_ai --cov-fail-under=90
python -m ruff check .
python -m build
twine check dist/*
```

## 2. Tag

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

Create the matching GitHub release from the changelog.

## 3. Publish the TypeScript SDK

Requires membership in the `@optimus-primex` npm organization and an
`NPM_TOKEN` with publish access (never commit it):

```bash
cd typescript
npm login
npm publish --access public
```

Verify with `npm view @optimus-primex/ai-client version` and install it in a
clean directory.

## 4. Publish the Python package

Preferred: PyPI Trusted Publishing via a GitHub Actions `pypi` environment
(no long-lived token). Manual fallback:

```bash
cd python
python -m build
twine upload dist/*
```

Verify with `pip install stellar-ai==<version>` in a clean virtualenv.

## Checklist

- [ ] `CHANGELOG.md` updated and version bumped
- [ ] Both test suites and linters pass
- [ ] `npm pack --dry-run` only includes `dist/` and package metadata
- [ ] `twine check dist/*` passes
- [ ] Tag and GitHub release created
- [ ] Packages installable in a clean environment
