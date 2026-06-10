# Usage

## Static HTML

Use `cold_soup` for pages that do not require JavaScript rendering.

```python
from souppot import cold_soup

soup = cold_soup("https://example.com")

if soup:
    print(soup.title.string)
```

`cold_soup` returns a `BeautifulSoup` object for HTML responses, a raw `requests.Response` for other successful response types, and `None` for missing URLs or non-200 responses.

## JavaScript-Rendered HTML

Use `hot_soup` when a page needs Playwright Chromium to render JavaScript before parsing.

```python
from souppot import hot_soup

soup = hot_soup("https://example.com", wait_selector=".loaded")

if soup:
    print(soup.select_one(".loaded").get_text(strip=True))
```

If `wait_selector` times out, `hot_soup` logs the timeout and parses whatever DOM is available.

## Downloads

Use `hot_pot` when a file should be downloaded through Playwright's request context.

```python
from souppot import hot_pot

path = hot_pot(
    "https://example.com/file.zip",
    "downloads/file.zip",
    referer="https://example.com",
)

print(path)
```

Parent directories for the destination path are created automatically.
