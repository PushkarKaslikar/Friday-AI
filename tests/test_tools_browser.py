"""Unit tests for Phase 2.5 Browser Tools executing through BaseTool."""

from app.platform.browser.browser_service import BrowserService
from app.tools.builtin.browser_tools import (
    ActiveTabTool,
    BrowserBackTool,
    BrowserForwardTool,
    BrowserReloadTool,
    BrowserSearchTool,
    BrowserStatusTool,
    CloseTabTool,
    CurrentPageTool,
    FocusBrowserTool,
    GetLinksTool,
    GetPageInfoTool,
    GetPageTextTool,
    GetTitleTool,
    ListTabsTool,
    NewTabTool,
    OpenBrowserTool,
    OpenUrlTool,
    SwitchTabTool,
)


def test_open_browser_and_status_tools():
    service = BrowserService()
    open_tool = OpenBrowserTool(service=service)
    res_open = open_tool.execute({"browser_type": "chrome"})
    assert res_open.success is True
    assert res_open.result_data["is_running"] is True

    status_tool = BrowserStatusTool(service=service)
    res_status = status_tool.execute({})
    assert res_status.success is True
    assert res_status.result_data["tab_count"] >= 1

    focus_tool = FocusBrowserTool(service=service)
    res_focus = focus_tool.execute({})
    assert res_focus.success is True


def test_open_url_and_page_reading_tools():
    service = BrowserService()
    open_url_tool = OpenUrlTool(service=service)
    res_nav = open_url_tool.execute({"url": "https://python.org"})
    assert res_nav.success is True

    page_tool = CurrentPageTool(service=service)
    res_page = page_tool.execute({})
    assert res_page.success is True

    title_tool = GetTitleTool(service=service)
    res_title = title_tool.execute({})
    assert res_title.success is True

    text_tool = GetPageTextTool(service=service)
    res_text = text_tool.execute({"max_length": 500})
    assert res_text.success is True

    info_tool = GetPageInfoTool(service=service)
    res_info = info_tool.execute({})
    assert res_info.success is True

    links_tool = GetLinksTool(service=service)
    res_links = links_tool.execute({"max_links": 10})
    assert res_links.success is True

    reload_tool = BrowserReloadTool(service=service)
    res_reload = reload_tool.execute({})
    assert res_reload.success is True

    back_tool = BrowserBackTool(service=service)
    res_back = back_tool.execute({})
    assert res_back.success is True

    fwd_tool = BrowserForwardTool(service=service)
    res_fwd = fwd_tool.execute({})
    assert res_fwd.success is True


def test_tab_management_tools():
    service = BrowserService()
    service.start_session()

    list_tool = ListTabsTool(service=service)
    res_list = list_tool.execute({})
    assert res_list.success is True

    new_tab_tool = NewTabTool(service=service)
    res_new = new_tab_tool.execute({"url": "https://github.com"})
    assert res_new.success is True
    new_tab_id = res_new.result_data["tab_id"]

    switch_tool = SwitchTabTool(service=service)
    res_switch = switch_tool.execute({"tab_id": new_tab_id})
    assert res_switch.success is True

    active_tool = ActiveTabTool(service=service)
    res_active = active_tool.execute({})
    assert res_active.result_data["tab_id"] == new_tab_id

    close_tool = CloseTabTool(service=service)
    res_close = close_tool.execute({"tab_id": new_tab_id})
    assert res_close.success is True
    assert res_close.result_data["closed"] is True


def test_browser_search_tool():
    service = BrowserService()
    search_tool = BrowserSearchTool(service=service)
    res_search = search_tool.execute({"query": "Friday AI Assistant"})
    assert res_search.success is True
    assert "duckduckgo" in res_search.result_data["url"].lower()
