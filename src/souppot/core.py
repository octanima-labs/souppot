from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pathlib import Path

import requests
import time
import tuning


logger = tuning.getLogger(__name__)


__all__ = [
    'cold_soup',
    'hot_soup',
    'hot_download'
]


def _clean_url(url: str | None) -> str | None:
    if url is None:
        return None
    url = str(url).strip()
    return url or None


def cold_soup(url: str | None, check_errors: bool = False) -> BeautifulSoup | requests.Response | None:
    url = _clean_url(url)
    if url is None:
        logger.warning(f"URL not provided")
        return None
    logger.debug(f"GET {url}")
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
    headers = {
        # Browser-like request headers to reduce naive bot blocking
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
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
    if origin:
        headers["Referer"] = origin + "/"

    res = requests.get(url=url, headers=headers, stream=True, timeout=15, allow_redirects=True)
    if check_errors:
        res.raise_for_status()
    if res.history:
        logger.debug(f"Redirected ({len(res.history)} hops) -> {res.url}")
        for hop in res.history:
            logger.debug(f"    {hop.status_code} {hop.url}")
    if res.status_code == 200:
        # logger.debug(f"response: {res.text}")
        ct = res.headers.get('Content-Type', '').lower()
        if 'text/html' in ct:
            _ = BeautifulSoup(res.text, 'html.parser')
            logger.debug(f"✅ Soup is served ({len(res.text)} chars)")
            return _
        else:
            logger.debug(f"Not an HTML page ({ct})")
            return res
    else:
        logger.error(f"HTTP error: {res.status_code}")
        return None


def hot_soup(
    url: str | None,
    wait_seconds: float = 3,
    wait_selector: str | None = None,
) -> BeautifulSoup | None:
    """
    Render a page in a headless browser (JS enabled) and return BeautifulSoup.
    """
    url = _clean_url(url)
    if url is None:
        logger.warning(f"URL not provided")
        return None

    logger.debug(f"RENDER {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1920, "height": 1080},
            )
            context.set_extra_http_headers(
                {
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "image/avif,image/webp,image/apng,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if page.url != url:
                status = response.status if response is not None else "?"
                logger.info(f"Redirected -> {page.url} (status: {status})")

            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=max(1000, int(wait_seconds * 1000)))
                except PlaywrightTimeoutError:
                    logger.error(f"Timeout waiting for selector: {wait_selector}")
                    # Continue anyway and parse whatever has been rendered so far.
            else:
                time.sleep(max(0, float(wait_seconds)))

            html = page.content()
            context.close()
            browser.close()

        _ = BeautifulSoup(html, 'html.parser')
        logger.debug(f"✅ Soup is served (JS-rendered - {len(html)} chars)")
        return _

    except Exception as e:
        logger.error(f"Playwright error: {e}")
        return None


def instant_soup(url):
    # like cold_soup, but for APIs. APIs do not need to fake the headers
    pass


def hot_download(url: str | None, dest: str | Path, referer: str | None = None, timeout_ms: int = 60_000) -> Path:
    """
    Download a binary using Playwright's network stack and save it to `dest`.
    """
    url = _clean_url(url)
    if url is None:
        raise ValueError("URL not provided")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"PLAYWRIGHT GET {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        headers = {
            "Accept": "application/octet-stream,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if referer:
            headers["Referer"] = referer

        response = context.request.get(
            url,
            headers=headers,
            fail_on_status_code=True,
            timeout=timeout_ms,
        )
        body = response.body()

        context.close()
        browser.close()

    with open(dest, "wb") as f:
        f.write(body)
    logger.debug(f"Download saved to: {dest}")
    return dest
