"""Unit tests for BrowserService and session management."""

from app.platform.browser.browser_service import BrowserService


def test_browser_service_lifecycle():
    service = BrowserService()
    status_start = service.start_session(headless=True)
    assert status_start.is_running is True
    assert status_start.tab_count >= 1

    health = service.health_check()
    assert health["status"] == "HEALTHY"

    service.stop_session()
    status_stop = service.get_status()
    assert status_stop.is_running is False


def test_browser_service_tabs_and_navigation():
    service = BrowserService()
    service.start_session(headless=True)

    nav_res = service.open_url("https://python.org")
    assert nav_res.success is True

    new_tab = service.new_tab("https://docs.python.org")
    assert new_tab.tab_id != ""

    tabs = service.list_tabs()
    assert len(tabs) == 2

    active = service.get_active_tab()
    assert active.tab_id == new_tab.tab_id

    service.stop_session()


def test_browser_service_search():
    service = BrowserService()
    service.start_session(headless=True)

    res = service.search("Python 3.12 release notes")
    assert res.success is True
    assert "duckduckgo" in res.url.lower()

    service.stop_session()
