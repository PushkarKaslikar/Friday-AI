"""Playwright-backed implementation of IBrowserController with mock fallback for test environments."""

import os
import uuid
from typing import Any

from app.logging import logger
from app.platform.browser.controller import IBrowserController
from app.platform.browser.models import (
    BrowserStatus,
    BrowserTab,
    NavigationResult,
    PageInfo,
    PageLink,
)
from app.platform.browser.url_security import UrlSecurityManager
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


class PlaywrightController(IBrowserController):
    """Playwright-backed browser automation controller with dedicated profile session management."""

    def __init__(self, url_security: UrlSecurityManager | None = None) -> None:
        self.url_security = url_security or UrlSecurityManager()
        self.session_id: str = ""
        self.browser_type_name: str = "chrome"
        self.is_active: bool = False

        # In-memory session representation
        self._tabs: dict[str, dict[str, Any]] = {}
        self._active_tab_id: str | None = None
        self._pw = None
        self._browser_context = None

    def start_session(
        self, browser_type: str = "chrome", headless: bool = True
    ) -> BrowserStatus:
        """Initialize browser session and create default tab."""
        if self.is_active:
            return self.get_status()

        self.session_id = str(uuid.uuid4())[:8]
        self.browser_type_name = browser_type
        self.is_active = True

        try:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            profile_dir = os.path.expandvars(r"%LOCALAPPDATA%\Friday\browser_profile")
            os.makedirs(profile_dir, exist_ok=True)

            b_type = (
                self._pw.chromium
                if browser_type in ("chrome", "chromium")
                else self._pw.firefox
            )
            self._browser_context = b_type.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
            )
            logger.info(
                f"PlaywrightController: Persistent browser context launched ({browser_type}, headless={headless})."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"PlaywrightController: Real browser launch unavailable, falling back to session stub: {exc}"
            )

        # Create default tab
        self.new_tab(url="about:blank")
        return self.get_status()

    def stop_session(self) -> None:
        """Close browser context and clean up resources."""
        if not self.is_active:
            return

        try:
            if self._browser_context:
                self._browser_context.close()
            if self._pw:
                self._pw.stop()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"PlaywrightController: Exception closing session: {exc}")
        finally:
            self._pw = None
            self._browser_context = None
            self.is_active = False
            self._tabs.clear()
            self._active_tab_id = None
            logger.info("PlaywrightController: Session stopped.")

    def get_status(self) -> BrowserStatus:
        """Query current browser status."""
        active_tab = self.get_active_tab()
        return BrowserStatus(
            is_running=self.is_active,
            browser_type=self.browser_type_name,
            tab_count=len(self._tabs),
            active_tab_id=self._active_tab_id,
            session_id=self.session_id,
            current_url=active_tab.url if active_tab else "",
            current_title=active_tab.title if active_tab else "",
        )

    def open_url(self, url: str) -> NavigationResult:
        """Navigate active tab to target URL."""
        if not self.is_active:
            self.start_session()

        clean_url = self.url_security.sanitize_url(url)
        active_tab_id = self._active_tab_id

        if not active_tab_id or active_tab_id not in self._tabs:
            tab = self.new_tab()
            active_tab_id = tab.tab_id

        tab_data = self._tabs[active_tab_id]

        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                res = page.goto(clean_url, timeout=15000)
                title = page.title()
                tab_data["url"] = page.url
                tab_data["title"] = title
                return NavigationResult(
                    success=res.ok if res else True,
                    url=page.url,
                    title=title,
                    tab_id=active_tab_id,
                )
            except Exception as exc:  # noqa: BLE001
                return NavigationResult(
                    success=False,
                    url=clean_url,
                    tab_id=active_tab_id,
                    error_message=str(exc),
                )

        # Mock fallback update
        domain = clean_url.split("//")[-1].split("/")[0]
        tab_data["url"] = clean_url
        tab_data["title"] = f"Friday Web - {domain}"

        return NavigationResult(
            success=True,
            url=clean_url,
            title=tab_data["title"],
            tab_id=active_tab_id,
        )

    def new_tab(self, url: str | None = None) -> BrowserTab:
        """Create a new tab with optional URL."""
        if not self.is_active:
            self.start_session()

        tab_id = f"tab_{len(self._tabs) + 1}_{str(uuid.uuid4())[:4]}"
        pw_page = None

        if self._browser_context:
            try:
                pw_page = self._browser_context.new_page()
                if url and url != "about:blank":
                    clean_url = self.url_security.sanitize_url(url)
                    pw_page.goto(clean_url, timeout=15000)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"PlaywrightController: Exception creating new page: {exc}"
                )

        initial_url = url if url else "about:blank"
        title = "New Tab"

        self._tabs[tab_id] = {
            "tab_id": tab_id,
            "title": title,
            "url": initial_url,
            "index": len(self._tabs),
            "pw_page": pw_page,
        }
        self._active_tab_id = tab_id

        if url and url != "about:blank" and not pw_page:
            self.open_url(url)

        return self.get_active_tab()  # type: ignore

    def close_tab(self, tab_id: str) -> bool:
        """Close a target tab by ID."""
        if tab_id not in self._tabs:
            return False

        tab_data = self._tabs.pop(tab_id)
        if tab_data.get("pw_page"):
            try:
                tab_data["pw_page"].close()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"PlaywrightController: Exception closing page: {exc}")

        if self._active_tab_id == tab_id:
            self._active_tab_id = next(iter(self._tabs.keys())) if self._tabs else None

        return True

    def switch_tab(self, tab_id: str) -> bool:
        """Switch active tab by tab ID."""
        if tab_id not in self._tabs:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Tab ID '{tab_id}' does not exist.",
            )

        self._active_tab_id = tab_id
        tab_data = self._tabs[tab_id]
        if tab_data.get("pw_page"):
            try:
                tab_data["pw_page"].bring_to_front()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"PlaywrightController: Exception switching tab: {exc}")
        return True

    def list_tabs(self) -> list[BrowserTab]:
        """List active browser tabs."""
        result = []
        for idx, (t_id, t_data) in enumerate(self._tabs.items()):
            result.append(
                BrowserTab(
                    tab_id=t_id,
                    title=t_data["title"],
                    url=t_data["url"],
                    index=idx,
                    active=(t_id == self._active_tab_id),
                )
            )
        return result

    def get_active_tab(self) -> BrowserTab | None:
        """Get active tab model details."""
        if not self._active_tab_id or self._active_tab_id not in self._tabs:
            return None

        t_data = self._tabs[self._active_tab_id]
        return BrowserTab(
            tab_id=self._active_tab_id,
            title=t_data["title"],
            url=t_data["url"],
            index=list(self._tabs.keys()).index(self._active_tab_id),
            active=True,
        )

    def go_back(self) -> NavigationResult:
        """Navigate back in history."""
        active = self.get_active_tab()
        if not active:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="No active tab available to navigate back.",
            )

        tab_data = self._tabs[active.tab_id]
        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                page.go_back(timeout=10000)
                tab_data["url"] = page.url
                tab_data["title"] = page.title()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlaywrightController: go_back failed: {exc}")

        return NavigationResult(
            success=True,
            url=tab_data["url"],
            title=tab_data["title"],
            tab_id=active.tab_id,
        )

    def go_forward(self) -> NavigationResult:
        """Navigate forward in history."""
        active = self.get_active_tab()
        if not active:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="No active tab available to navigate forward.",
            )

        tab_data = self._tabs[active.tab_id]
        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                page.go_forward(timeout=10000)
                tab_data["url"] = page.url
                tab_data["title"] = page.title()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlaywrightController: go_forward failed: {exc}")

        return NavigationResult(
            success=True,
            url=tab_data["url"],
            title=tab_data["title"],
            tab_id=active.tab_id,
        )

    def reload_page(self) -> NavigationResult:
        """Reload active page."""
        active = self.get_active_tab()
        if not active:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="No active tab available to reload.",
            )

        tab_data = self._tabs[active.tab_id]
        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                page.reload(timeout=10000)
                tab_data["url"] = page.url
                tab_data["title"] = page.title()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlaywrightController: reload failed: {exc}")

        return NavigationResult(
            success=True,
            url=tab_data["url"],
            title=tab_data["title"],
            tab_id=active.tab_id,
        )

    def get_page_text(self, max_length: int = 20000) -> tuple[str, bool]:
        """Extract visible text from active page with truncation limit."""
        active = self.get_active_tab()
        if not active:
            return "", False

        tab_data = self._tabs[active.tab_id]
        text_content = f"Page Content for {active.title} ({active.url})"

        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                text_content = page.inner_text("body")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlaywrightController: get_page_text failed: {exc}")

        is_truncated = len(text_content) > max_length
        final_text = text_content[:max_length] if is_truncated else text_content
        return final_text, is_truncated

    def get_page_info(self) -> PageInfo:
        """Get summary metadata of current active page."""
        active = self.get_active_tab()
        if not active:
            return PageInfo(
                url="", title="", text_length=0, link_count=0, truncated=False
            )

        text, truncated = self.get_page_text()
        links = self.get_links()

        return PageInfo(
            url=active.url,
            title=active.title,
            text_length=len(text),
            link_count=len(links),
            truncated=truncated,
        )

    def get_links(self, max_links: int = 50) -> list[PageLink]:
        """Extract structured hyperlinks from active page."""
        active = self.get_active_tab()
        if not active:
            return []

        tab_data = self._tabs[active.tab_id]
        links: list[PageLink] = []

        if tab_data.get("pw_page"):
            try:
                page = tab_data["pw_page"]
                elements = page.query_selector_all("a[href]")
                for el in elements[:max_links]:
                    href = el.get_attribute("href")
                    txt = el.inner_text().strip() or "Link"
                    if href and href.startswith("http"):
                        links.append(PageLink(text=txt, url=href))
                return links
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"PlaywrightController: get_links failed: {exc}")

        # Mock fallback links
        links.append(PageLink(text="Home", url=active.url))
        return links

    def focus_browser(self) -> bool:
        """Bring browser window to foreground."""
        active = self.get_active_tab()
        if not active:
            return False

        tab_data = self._tabs[active.tab_id]
        if tab_data.get("pw_page"):
            try:
                tab_data["pw_page"].bring_to_front()
                return True
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"PlaywrightController: Exception focusing browser: {exc}")
                return False
        return True
