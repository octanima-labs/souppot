from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from souppot import cold_soup, hot_download, hot_soup


pytestmark = pytest.mark.functional

FIXTURES = Path(__file__).parent / "fixtures"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return None


@pytest.fixture(scope="module")
def fixture_server() -> str:
    handler = partial(QuietHandler, directory=str(FIXTURES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def chromium_available() -> None:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright Chromium is not available: {exc}")


def test_cold_soup_fetches_local_html(fixture_server: str) -> None:
    soup = cold_soup(f"{fixture_server}/page.html")

    assert isinstance(soup, BeautifulSoup)
    assert soup.select_one("#title").get_text(strip=True) == "Souppot Functional Fixture"
    assert soup.select_one(".static").get_text(strip=True) == "This element is present in the original HTML."
    assert soup.select_one(".delayed") is None


def test_hot_soup_waits_for_javascript_created_element(
    fixture_server: str,
    chromium_available: None,
) -> None:
    soup = hot_soup(f"{fixture_server}/page.html", wait_selector=".delayed", wait_seconds=2)

    assert isinstance(soup, BeautifulSoup)
    assert soup.select_one(".delayed").get_text(strip=True) == "This element was created by JavaScript."


def test_hot_download_downloads_local_file(
    fixture_server: str,
    chromium_available: None,
    tmp_path: Path,
) -> None:
    source = FIXTURES / "dummy.bin"
    dest = tmp_path / "downloads" / "dummy.bin"

    result = hot_download(f"{fixture_server}/dummy.bin", dest, referer=f"{fixture_server}/page.html")

    assert result == dest
    assert dest.read_bytes() == source.read_bytes()
