"""Browser service managing browser session lifecycle, tab management, web reading, and navigation."""

from typing import Any
from urllib.parse import quote_plus

from app.platform.browser.controller import IBrowserController
from app.platform.browser.models import (
    BrowserStatus,
    BrowserTab,
    NavigationResult,
    PageInfo,
    PageLink,
)
from app.platform.browser.playwright_controller import PlaywrightController
from app.platform.browser.url_security import UrlSecurityManager
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

DEFAULT_SEARCH_ENGINE_URL: str = "https://html.duckduckgo.com/html/?q="


class BrowserService:
    """Core browser service managing session lifecycle, tab tracking, web navigation, and visible page text reading."""

    def __init__(
        self,
        controller: IBrowserController | None = None,
        url_security: UrlSecurityManager | None = None,
        search_engine_base: str = DEFAULT_SEARCH_ENGINE_URL,
    ) -> None:
        self.url_security = url_security or UrlSecurityManager()
        self.controller = controller or PlaywrightController(
            url_security=self.url_security
        )
        self.search_engine_base = search_engine_base

    def start_session(
        self, browser_type: str = "chrome", headless: bool = True
    ) -> BrowserStatus:
        """Initialize or reuse a persistent browser session."""
        return self.controller.start_session(
            browser_type=browser_type, headless=headless
        )

    def stop_session(self) -> None:
        """Stop browser session and clean up resources."""
        self.controller.stop_session()

    def get_status(self) -> BrowserStatus:
        """Query current browser status."""
        return self.controller.get_status()

    def health_check(self) -> dict[str, Any]:
        """Diagnostic health check payload for BrowserService."""
        status = self.get_status()
        return {
            "status": "HEALTHY" if status.is_running else "STOPPED",
            "is_running": status.is_running,
            "browser_type": status.browser_type,
            "tab_count": status.tab_count,
            "active_tab_id": status.active_tab_id,
            "session_id": status.session_id,
        }

    def open_url(self, url: str) -> NavigationResult:
        """Navigate active tab to target URL."""
        return self.controller.open_url(url)

    def new_tab(self, url: str | None = None) -> BrowserTab:
        """Create a new tab with optional URL."""
        return self.controller.new_tab(url=url)

    def close_tab(self, tab_id: str) -> bool:
        """Close target tab by tab ID."""
        return self.controller.close_tab(tab_id)

    def switch_tab(self, tab_id: str) -> bool:
        """Switch active tab by tab ID."""
        return self.controller.switch_tab(tab_id)

    def list_tabs(self) -> list[BrowserTab]:
        """List all active browser tabs."""
        return self.controller.list_tabs()

    def get_active_tab(self) -> BrowserTab | None:
        """Get active tab details."""
        return self.controller.get_active_tab()

    def go_back(self) -> NavigationResult:
        """Navigate back in history."""
        return self.controller.go_back()

    def go_forward(self) -> NavigationResult:
        """Navigate forward in history."""
        return self.controller.go_forward()

    def reload_page(self) -> NavigationResult:
        """Reload active page."""
        return self.controller.reload_page()

    def get_page_text(self, max_length: int = 20000) -> tuple[str, bool]:
        """Extract visible text from page."""
        return self.controller.get_page_text(max_length=max_length)

    def get_page_info(self) -> PageInfo:
        """Get summary metadata of current active page."""
        return self.controller.get_page_info()

    def get_links(self, max_links: int = 50) -> list[PageLink]:
        """Extract structured hyperlinks from active page."""
        return self.controller.get_links(max_links=max_links)

    def focus_browser(self) -> bool:
        """Bring browser window to foreground."""
        return self.controller.focus_browser()

    def search(self, query: str) -> NavigationResult:
        """Execute web search query on configured search engine."""
        clean_query = query.strip()
        if not clean_query:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="Search query string cannot be empty.",
            )

        target_url = self.search_engine_base + quote_plus(clean_query)
        return self.open_url(target_url)
