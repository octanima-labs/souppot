# AGENTS.md

## Current State
- This repo now uses a Hatchling `src` layout: package code lives under `src/souppot/`.
- The original script implementation is in `src/souppot/core.py`; `src/souppot/__init__.py` re-exports the public API.
- `tests/` contains unit tests plus local functional tests; there is no lockfile yet.
- GitHub Actions live in `.github/workflows/`: `ci.yml` runs on manual dispatch and pushes to `main`; `docs.yml` runs on manual dispatch and pushes to `docs`; `release.yml` runs on manual dispatch and `v*` tags.

## Script API
- The exported API is defined by `__all__`: `cold_soup`, `hot_soup`, and `hot_pot`.
- `cold_soup` uses `requests` with browser-like headers, returns `BeautifulSoup` for `text/html`, returns the raw `requests.Response` for other 200 responses, and returns `None` for missing URLs or non-200 responses unless `check_errors=True` raises first.
- `hot_soup` and `hot_pot` require Playwright Chromium; `hot_soup` returns `None` on Playwright errors and continues parsing if `wait_selector` times out.
- `hot_pot` creates destination parent directories and writes the response body to `dest` using Playwright's request context.

## Dependencies And Verification
- Runtime dependencies in `pyproject.toml` are `beautifulsoup4`, `requests`, `playwright`, and `2ning`; import `2ning` in code as `tuning`.
- Playwright users need Chromium installed via `python -m playwright install chromium`.
- Use Hatch for the dev environment; `hatch run pytest` installs/syncs dev tools and runs the configured test suite.
- Run only unit tests with `hatch run pytest tests/test_core.py`.
- Run functional tests with `hatch run pytest tests/functional`; Playwright-backed tests skip if Chromium is unavailable.
- Run type checks with `hatch run mypy src/souppot`; `pyproject.toml` ignores missing imports for `tuning` because `2ning` does not ship type stubs.
- Build docs with `hatch run docs:build`; docs use Sphinx, MyST, and the PyData theme from `docs/`.
- CI quality checks are `hatch run ruff format --check .`, `hatch run ruff check .`, `hatch run mypy src/souppot`, unit tests, functional tests with Chromium installed, and `hatch run python -m build`.
- Release workflow builds sdists/wheels, checks metadata with Twine, publishes to PyPI via trusted publishing, and uploads `dist/*` to the GitHub Release.
- The smallest syntax sanity check is `python -m py_compile src/souppot/__init__.py src/souppot/core.py tests/test_core.py tests/functional/test_functional.py`.

## Testing Notes
- Unit tests in `tests/test_core.py` mock `requests.get` and `sync_playwright`; do not add real HTTP or browser execution there.
- Unit fixture HTML lives in `tests/fixtures/basic.html`.
- Functional fixtures live in `tests/functional/fixtures/`; `page.html` creates `.delayed` via JavaScript and `dummy.bin` simulates a download.
- Functional tests serve fixtures via a local threaded `http.server`; do not add external network dependencies there.

## Docs
Build the documentation with:

```bash
hatch run docs:build
```
