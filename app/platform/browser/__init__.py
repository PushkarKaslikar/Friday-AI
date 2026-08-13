"""Browser platform engine package providing URL security, controller contracts, and persistent session management."""

from app.platform.browser.browser_service import BrowserService
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

__all__ = [
    "BrowserService",
    "BrowserStatus",
    "BrowserTab",
    "IBrowserController",
    "NavigationResult",
    "PageInfo",
    "PageLink",
    "PlaywrightController",
    "UrlSecurityManager",
]
