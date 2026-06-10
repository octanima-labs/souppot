from pathlib import Path

import pytest
import souppot
from bs4 import BeautifulSoup
from souppot import core


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
        url: str = "https://example.com/page",
        history: list[object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.url = url
        self.history = history or []
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error


class FakeRenderedResponse:
    status = 200


class FakePage:
    def __init__(self, html: str, *, wait_raises: bool = False) -> None:
        self.html = html
        self.url = "https://example.com/page"
        self.wait_raises = wait_raises
        self.wait_selector_calls: list[tuple[str, int]] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeRenderedResponse:
        self.url = url
        self.goto_call = {"url": url, "wait_until": wait_until, "timeout": timeout}
        return FakeRenderedResponse()

    def wait_for_selector(self, selector: str, *, timeout: int) -> None:
        self.wait_selector_calls.append((selector, timeout))
        if self.wait_raises:
            raise core.PlaywrightTimeoutError("selector timed out")

    def content(self) -> str:
        return self.html


class FakeBrowserContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.extra_headers: dict[str, str] | None = None
        self.closed = False

    def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        self.extra_headers = headers

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeBrowserContext) -> None:
        self.context = context
        self.closed = False

    def new_context(self, **kwargs: object) -> FakeBrowserContext:
        self.new_context_kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser

    def launch(self, *, headless: bool) -> FakeBrowser:
        self.launch_kwargs = {"headless": headless}
        return self.browser


class FakeSyncPlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium

    def __enter__(self) -> "FakeSyncPlaywright":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeDownloadResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def body(self) -> bytes:
        return self._body


class FakeRequestContext:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> FakeDownloadResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeDownloadResponse(self.body)


class FakeDownloadContext:
    def __init__(self, body: bytes) -> None:
        self.request = FakeRequestContext(body)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeDownloadBrowser:
    def __init__(self, context: FakeDownloadContext) -> None:
        self.context = context
        self.closed = False

    def new_context(self, **kwargs: object) -> FakeDownloadContext:
        self.new_context_kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeDownloadChromium:
    def __init__(self, browser: FakeDownloadBrowser) -> None:
        self.browser = browser

    def launch(self, *, headless: bool) -> FakeDownloadBrowser:
        self.launch_kwargs = {"headless": headless}
        return self.browser


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "basic.html").read_text(encoding="utf-8")


def test_package_exports_public_api() -> None:
    assert souppot.__all__ == ("cold_soup", "hot_soup", "hot_download")
    assert souppot.cold_soup is core.cold_soup
    assert souppot.hot_soup is core.hot_soup
    assert souppot.hot_download is core.hot_download


@pytest.mark.parametrize("url", [None, "", "   "])
def test_cold_soup_missing_url_returns_none_without_request(
    monkeypatch: pytest.MonkeyPatch, url: str | None
) -> None:
    def fail_get(**kwargs: object) -> None:
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr(core.requests, "get", fail_get)

    assert core.cold_soup(url) is None


def test_cold_soup_sends_browser_like_request_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(headers={"Content-Type": "application/json"})
    calls: list[dict[str, object]] = []

    def fake_get(**kwargs: object) -> FakeResponse:
        calls.append(kwargs)
        return response

    monkeypatch.setattr(core.requests, "get", fake_get)

    assert core.cold_soup(" https://example.com/path ") is response
    call = calls[0]
    headers = call["headers"]

    assert call["url"] == "https://example.com/path"
    assert "stream" not in call
    assert call["timeout"] == 15
    assert call["allow_redirects"] is True
    assert isinstance(headers, dict)
    assert "Mozilla/5.0" in headers["User-Agent"]
    assert headers["Referer"] == "https://example.com/"


def test_cold_soup_returns_beautifulsoup_for_html_response(
    monkeypatch: pytest.MonkeyPatch,
    fixture_html: str,
) -> None:
    response = FakeResponse(
        text=fixture_html, headers={"Content-Type": "text/html; charset=utf-8"}
    )

    monkeypatch.setattr(core.requests, "get", lambda **kwargs: response)

    soup = core.cold_soup("https://example.com/page")

    assert isinstance(soup, BeautifulSoup)
    assert soup.select_one("#title").get_text(strip=True) == "Soup Pot"


def test_cold_soup_returns_response_for_non_html_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        text='{"ok": true}', headers={"Content-Type": "application/json"}
    )

    monkeypatch.setattr(core.requests, "get", lambda **kwargs: response)

    assert core.cold_soup("https://example.com/data.json") is response


def test_cold_soup_returns_none_for_non_200_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(status_code=404, headers={"Content-Type": "text/html"})

    monkeypatch.setattr(core.requests, "get", lambda **kwargs: response)

    assert core.cold_soup("https://example.com/missing") is None


def test_cold_soup_check_errors_raises_before_status_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MarkerError(Exception):
        pass

    response = FakeResponse(status_code=500, error=MarkerError("boom"))

    monkeypatch.setattr(core.requests, "get", lambda **kwargs: response)

    with pytest.raises(MarkerError):
        core.cold_soup("https://example.com/error", check_errors=True)


@pytest.mark.parametrize("url", [None, "", "   "])
def test_hot_soup_missing_url_returns_none_without_playwright(
    monkeypatch: pytest.MonkeyPatch, url: str | None
) -> None:
    def fail_sync_playwright() -> None:
        raise AssertionError("sync_playwright should not be called")

    monkeypatch.setattr(core, "sync_playwright", fail_sync_playwright)

    assert core.hot_soup(url) is None


def test_hot_soup_parses_rendered_html_from_fake_playwright(
    monkeypatch: pytest.MonkeyPatch,
    fixture_html: str,
) -> None:
    page = FakePage(fixture_html)
    context = FakeBrowserContext(page)
    browser = FakeBrowser(context)
    playwright = FakeSyncPlaywright(FakeChromium(browser))
    sleep_calls: list[float] = []

    monkeypatch.setattr(core, "sync_playwright", lambda: playwright)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    soup = core.hot_soup("https://example.com/page", wait_seconds=0)

    assert isinstance(soup, BeautifulSoup)
    assert (
        soup.select_one(".message").get_text(strip=True)
        == "Fixture HTML for parser unit tests."
    )
    assert sleep_calls == [0]
    assert context.closed is True
    assert browser.closed is True


def test_hot_soup_wait_selector_timeout_still_parses_html(
    monkeypatch: pytest.MonkeyPatch,
    fixture_html: str,
) -> None:
    page = FakePage(fixture_html, wait_raises=True)
    context = FakeBrowserContext(page)
    browser = FakeBrowser(context)
    playwright = FakeSyncPlaywright(FakeChromium(browser))

    monkeypatch.setattr(core, "sync_playwright", lambda: playwright)

    soup = core.hot_soup(
        "https://example.com/page", wait_selector="#missing", wait_seconds=0.2
    )

    assert isinstance(soup, BeautifulSoup)
    assert soup.select_one("#content") is not None
    assert page.wait_selector_calls == [("#missing", 1000)]


@pytest.mark.parametrize("url", [None, "", "   "])
def test_hot_download_missing_url_raises_value_error(
    url: str | None, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="URL not provided"):
        core.hot_download(url, tmp_path / "out.bin")


def test_hot_download_creates_parent_dirs_and_writes_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = b"downloaded bytes"
    context = FakeDownloadContext(body)
    browser = FakeDownloadBrowser(context)
    playwright = FakeSyncPlaywright(FakeDownloadChromium(browser))
    dest = tmp_path / "nested" / "out.bin"

    monkeypatch.setattr(core, "sync_playwright", lambda: playwright)

    result = core.hot_download(
        " https://example.com/file.bin ",
        dest,
        referer="https://example.com/page",
        timeout_ms=123,
    )

    assert result == dest
    assert dest.read_bytes() == body
    assert context.closed is True
    assert browser.closed is True

    call = context.request.calls[0]
    headers = call["headers"]
    assert call["url"] == "https://example.com/file.bin"
    assert call["fail_on_status_code"] is True
    assert call["timeout"] == 123
    assert isinstance(headers, dict)
    assert headers["Referer"] == "https://example.com/page"
