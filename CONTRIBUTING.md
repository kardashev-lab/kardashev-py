# Contributing to kardashev

Thanks for helping make US grid data easier to access in Python. This package gives direct, no-API-key access to CAISO, ERCOT, MISO, NYISO, ISONE, SPP, and PJM, plus an optional client for the full Kardashev Labs API.

## What this repo does

- `CAISO`, `ERCOT`, `MISO`, `NYISO`, `ISONE`, `SPP` classes: scrape each ISO's public data feed directly, no API key.
- `Client`: talks to the hosted Kardashev Labs API at `https://data.kardashevlabs.org` for carbon intensity, LMP history, interconnection queues, and 20+ more endpoints.

Stack: Python 3.9+, `httpx`, `pandas`.

## Local setup

```bash
git clone https://github.com/kardashev-lab/kardashev-py
cd kardashev-py
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Before opening a PR

- Run `pytest` and make sure it passes.
- If you add or change an ISO parser, include a real (or realistic sample) response you tested against - ISO feeds change format without notice, and a live example makes review much faster.
- Update `CHANGELOG.md` with a one-line summary under a new version heading.
- Bump `version` in `pyproject.toml` and `__version__` in `kardashev/__init__.py` together - they must match.

## Good first contributions

- Add a missing dataset for an ISO that already has a class (e.g., `get_generation()` for an ISO that only has `get_fuel_mix()`).
- Improve error messages when an ISO feed is down or returns an unexpected shape.
- Add a new example script under `examples/`.
- Improve type hints or docstrings on existing methods.

## PR guidelines

- Keep changes scoped to one ISO or one endpoint where possible.
- Do not hard-code credentials (ISONE requires `ISONE_USERNAME`/`ISONE_PASSWORD` env vars - never commit real values).
- Mention which ISO(s) and Python version you tested against.
