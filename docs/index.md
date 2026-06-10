# souppot

Small helpers for fetching and parsing HTML with `requests` or Playwright.

Use `cold_soup` for normal server-rendered HTML, `hot_soup` for JavaScript-rendered pages, and `hot_pot` when a download needs Playwright's browser-like request stack.

```{toctree}
:maxdepth: 2
:caption: Contents

usage
api
```

## Installation

From a checkout:

```bash
pip install .
```

When published to PyPI:

```bash
pip install souppot
```

For JavaScript-rendered pages and Playwright-backed downloads, install Chromium:

```bash
python -m playwright install chromium
```

## License

souppot is released under the MIT license.
