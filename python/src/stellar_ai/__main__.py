"""Run the service: ``python -m stellar_ai`` or ``stellar-ai``."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("stellar_ai.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
