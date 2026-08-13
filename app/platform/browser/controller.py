"""Abstract interface contract for local desktop browser automation controllers."""

from abc import ABC, abstractmethod

from app.platform.browser.models import (
    BrowserStatus,
    BrowserTab,
    NavigationResult,
    PageInfo,
    PageLink,
)


class IBrowserController(ABC):
    """Abstract interface contract for browser controllers."""

    @abstractmethod
    def start_session(
        self, browser_type: str = "chrome", headless: bool = True
    ) -> BrowserStatus:
        """Initialize or reuse a browser session."""

    @abstractmethod
    def stop_session(self) -> None:
        """Close browser session and clean up resources."""

    @abstractmethod
    def get_status(self) -> BrowserStatus:
        """Query current browser status."""

    @abstractmethod
    def open_url(self, url: str) -> NavigationResult:
        """Navigate active tab to target URL."""

    @abstractmethod
    def new_tab(self, url: str | None = None) -> BrowserTab:
        """Create a new tab with optional URL."""

    @abstractmethod
    def close_tab(self, tab_id: str) -> bool:
        """Close a specific tab by tab ID."""

    @abstractmethod
    def switch_tab(self, tab_id: str) -> bool:
        """Switch active tab by tab ID."""

    @abstractmethod
    def list_tabs(self) -> list[BrowserTab]:
        """List active browser tabs."""

    @abstractmethod
    def get_active_tab(self) -> BrowserTab | None:
        """Get active tab details."""

    @abstractmethod
    def go_back(self) -> NavigationResult:
        """Navigate back in history."""

    @abstractmethod
    def go_forward(self) -> NavigationResult:
        """Navigate forward in history."""

    @abstractmethod
    def reload_page(self) -> NavigationResult:
        """Reload active page."""

    @abstractmethod
    def get_page_text(self, max_length: int = 20000) -> tuple[str, bool]:
        """Extract visible text from page, returning (text, is_truncated)."""

    @abstractmethod
    def get_page_info(self) -> PageInfo:
        """Get summary metadata of current active page."""

    @abstractmethod
    def get_links(self, max_links: int = 50) -> list[PageLink]:
        """Extract structured hyperlinks from active page."""

    @abstractmethod
    def focus_browser(self) -> bool:
        """Bring browser window to foreground."""
