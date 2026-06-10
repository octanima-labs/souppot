# AGENTS.md

## Current State
- This repo now uses a Hatchling `src` layout: package code lives under `src/souppot/`.
- The original script implementation is in `src/souppot/core.py`; `src/souppot/__init__.py` re-exports the public API.
- `tests/` contains unit tests plus local functional tests; there is no lockfile or CI yet.

## Script API
- The exported API is defined by `__all__`: `cold_soup`, `hot_soup`, and `hot_download`.
- `instant_soup` is a stub and is not exported.
- `cold_soup` uses `requests` with browser-like headers, returns `BeautifulSoup` for `text/html`, returns the raw `requests.Response` for other 200 responses, and returns `None` for missing URLs or non-200 responses unless `check_errors=True` raises first.
- `hot_soup` and `hot_download` require Playwright Chromium; `hot_soup` returns `None` on Playwright errors and continues parsing if `wait_selector` times out.
- `hot_download` creates destination parent directories and writes the response body to `dest` using Playwright's request context.

## Dependencies And Verification
- Runtime dependencies in `pyproject.toml` are `beautifulsoup4`, `requests`, `playwright`, and `2ning`; import `2ning` in code as `tuning`.
- Playwright users need Chromium installed via `python -m playwright install chromium`.
- Use Hatch for the dev environment; `hatch run pytest` installs/syncs dev tools and runs the configured test suite.
- Run only unit tests with `hatch run pytest tests/test_core.py`.
- Run functional tests with `hatch run pytest tests/functional`; Playwright-backed tests skip if Chromium is unavailable.
- The smallest syntax sanity check is `python -m py_compile src/souppot/__init__.py src/souppot/core.py tests/test_core.py tests/functional/test_functional.py`.

## Testing Notes
- Unit tests in `tests/test_core.py` mock `requests.get` and `sync_playwright`; do not add real HTTP or browser execution there.
- Unit fixture HTML lives in `tests/fixtures/basic.html`.
- Functional fixtures live in `tests/functional/fixtures/`; `page.html` creates `.delayed` via JavaScript and `dummy.bin` simulates a download.
- Functional tests serve fixtures via a local threaded `http.server`; do not add external network dependencies there.
