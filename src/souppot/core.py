"""Core helpers for fetching static pages, rendered pages, and downloads.

``cold_soup`` uses ``requests`` for normal HTTP responses. ``hot_soup`` and
``hot_pot`` use Playwright Chromium for JavaScript-rendered pages and
browser-like download requests.
"""

import time
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import requests
import tuning
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Browser
from playwright.sync_api import BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


logger = tuning.getLogger(__name__)

BROWSER_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
HTML_ACCEPT: Final[str] = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,image/apng,*/*;q=0.8"
)
HTML_HEADERS: Final[dict[str, str]] = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": HTML_ACCEPT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
PLAYWRIGHT_HTML_HEADERS: Final[dict[str, str]] = {
    "Accept": HTML_ACCEPT,
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}
DOWNLOAD_HEADERS: Final[dict[str, str]] = {
    "Accept": "application/octet-stream,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

__all__: Final[tuple[str, ...]] = ("cold_soup", "hot_soup", "hot_pot")


def _clean_url(url: str | None) -> str | None:
    """Strip URL input and normalize missing values to ``None``."""
    if url is None:
        return None
    url = str(url).strip()
    return url or None


def cold_soup(
    url: str | None,
    check_errors: bool = False,
) -> BeautifulSoup | requests.Response | None:
    """Fetch a URL with ``requests`` and parse HTML responses.

    Args:
        url: URL to fetch. ``None`` and blank strings are treated as missing.
        check_errors: If true, call ``raise_for_status()`` before normal status
            handling.

    Returns:
        ``BeautifulSoup`` for ``200`` responses with a ``text/html`` content
        type, the raw ``requests.Response`` for other ``200`` responses, and
        ``None`` for missing URLs or non-``200`` responses.

    Raises:
        requests.HTTPError: If ``check_errors`` is true and the response status
            is an HTTP error.
    """
    url = _clean_url(url)
    if url is None:
        logger.warning("URL not provided")
        return None
    logger.debug("GET %s", url)
    parsed = urlparse(url)
    origin = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme and parsed.netloc
        else None
    )
    headers = HTML_HEADERS.copy()
    if origin:
        headers["Referer"] = origin + "/"

    res = requests.get(url=url, headers=headers, timeout=15, allow_redirects=True)
    if check_errors:
        res.raise_for_status()
    if res.history:
        logger.debug("Redirected (%s hops) -> %s", len(res.history), res.url)
        for hop in res.history:
            logger.debug("    %s %s", hop.status_code, hop.url)
    if res.status_code != 200:
        logger.error("HTTP error: %s", res.status_code)
        return None

    ct = res.headers.get("Content-Type", "").lower()
    if "text/html" not in ct:
        logger.debug("Not an HTML page (%s)", ct)
        return res

    soup = BeautifulSoup(res.text, "html.parser")
    logger.debug("✅ Soup is served (%s chars)", len(res.text))
    return soup


def hot_soup(
    url: str | None,
    wait_seconds: float = 3,
    wait_selector: str | None = None,
) -> BeautifulSoup | None:
    """Render a URL with Playwright Chromium and parse the final DOM.

    Args:
        url: URL to render. ``None`` and blank strings are treated as missing.
        wait_seconds: Seconds to sleep after ``domcontentloaded`` when no
            ``wait_selector`` is provided. When waiting for a selector, this is
            converted to the selector timeout with a minimum of 1000 ms.
        wait_selector: Optional CSS selector to wait for before parsing. If the
            selector times out, the currently rendered DOM is parsed anyway.

    Returns:
        ``BeautifulSoup`` for the rendered page, or ``None`` for missing URLs or
        Playwright errors.
    """
    url = _clean_url(url)
    if url is None:
        logger.warning("URL not provided")
        return None

    logger.debug("RENDER %s", url)
    try:
        with sync_playwright() as p:
            browser: Browser | None = None
            context: BrowserContext | None = None
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=BROWSER_USER_AGENT,
                    locale="en-US",
                    viewport={"width": 1920, "height": 1080},
                )
                context.set_extra_http_headers(PLAYWRIGHT_HTML_HEADERS.copy())

                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                if page.url != url:
                    status = response.status if response is not None else "?"
                    logger.info("Redirected -> %s (status: %s)", page.url, status)

                if wait_selector:
                    try:
                        page.wait_for_selector(
                            wait_selector,
                            timeout=max(1000, int(wait_seconds * 1000)),
                        )
                    except PlaywrightTimeoutError:
                        logger.error("Timeout waiting for selector: %s", wait_selector)
                        # Continue anyway and parse whatever has been rendered so far.
                else:
                    time.sleep(max(0, float(wait_seconds)))

                html = page.content()
            finally:
                if context is not None:
                    context.close()
                if browser is not None:
                    browser.close()

        soup = BeautifulSoup(html, "html.parser")
        logger.debug("✅ Soup is served (JS-rendered - %s chars)", len(html))
        return soup

    except PlaywrightError as e:
        logger.error("Playwright error: %s", e, exc_info=True)
        return None


def hot_pot(
    url: str | None,
    dest: str | Path,
    referer: str | None = None,
    timeout_ms: int = 60_000,
) -> Path:
    """Download a URL with Playwright's request context and save it to disk.

    Args:
        url: URL to download. ``None`` and blank strings raise ``ValueError``.
        dest: Destination file path. Parent directories are created if needed.
        referer: Optional ``Referer`` header to send with the request.
        timeout_ms: Playwright request timeout in milliseconds.

    Returns:
        The destination path as a ``Path``.

    Raises:
        ValueError: If ``url`` is missing.
        playwright.sync_api.Error: If Playwright cannot complete the request.
    """
    url = _clean_url(url)
    if url is None:
        raise ValueError("URL not provided")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.debug("PLAYWRIGHT GET %s", url)
    with sync_playwright() as p:
        browser: Browser | None = None
        context: BrowserContext | None = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=BROWSER_USER_AGENT,
                locale="en-US",
            )

            headers = DOWNLOAD_HEADERS.copy()
            if referer:
                headers["Referer"] = referer

            response = context.request.get(
                url,
                headers=headers,
                fail_on_status_code=True,
                timeout=timeout_ms,
            )
            body = response.body()
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()

    dest.write_bytes(body)
    logger.debug("Download saved to: %s", dest)
    return dest
