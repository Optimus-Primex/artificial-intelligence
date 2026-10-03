# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately using GitHub's [private vulnerability reporting][pvr]
(the **Security** tab → *Report a vulnerability*) or email the maintainers at
the address listed on the organisation profile.

Please include:

- a description of the issue and its impact,
- steps to reproduce (proof of concept if possible),
- affected version/commit.

We aim to acknowledge reports within a few days and will credit reporters who
want attribution.

## Scope

In scope:

- the Python service (`python/`) and TypeScript SDK (`typescript/`),
- authentication, input validation, and outbound request handling,
- dependency vulnerabilities.

## Handling secrets

- The service reads configuration from `STELLAR_AI_*` environment variables.
- Never commit API keys, tokens, or private keys. `.env` is git-ignored and
  `.env.example` contains placeholders only.
- CI runs [`scripts/scan_secrets.py`](scripts/scan_secrets.py), `pip-audit` and
  `bandit`; enable GitHub secret scanning on the repository as well.

[pvr]: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability
