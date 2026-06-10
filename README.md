# souppot

Small helpers for fetching and parsing HTML with `requests` or Playwright.

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

## Usage

Fetch static HTML:

```python
from souppot import cold_soup

soup = cold_soup("https://example.com")

if soup:
    print(soup.title.string)
```

Fetch JavaScript-rendered HTML:

```python
from souppot import hot_soup

soup = hot_soup("https://example.com", wait_selector=".loaded")

if soup:
    print(soup.select_one(".loaded").get_text(strip=True))
```

Download a file with Playwright:

```python
from souppot import hot_pot

path = hot_pot(
    "https://example.com/file.zip",
    "downloads/file.zip",
    referer="https://example.com",
)

print(path)
```

## Documentation

Documentation sources live in [docs/](docs/). Build them with:

```bash
hatch run docs:build
```

## License

MIT. See [LICENSE](LICENSE).
