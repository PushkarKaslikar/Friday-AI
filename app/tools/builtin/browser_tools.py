"""Browser interaction tools for opening, navigating, reading, and managing web tabs."""

from typing import Any

from pydantic import BaseModel, Field

from app.platform.browser.browser_service import BrowserService
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory


# 1. Open Browser Tool
class OpenBrowserInput(BaseModel):
    """Input parameters for OpenBrowserTool."""

    browser_type: str = Field(
        default="chrome", description="Browser type (chrome, edge)"
    )
    url: str | None = Field(
        default=None, description="Optional initial URL string to navigate to"
    )


class OpenBrowserTool(BaseTool):
    """Tool launching or reusing a persistent browser session."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.open",
            name="open_browser",
            display_name="Open Browser",
            description="Launches or reuses a local desktop browser session.",
            category=ToolCategory.MEDIA,
            tags=["browser", "web", "open", "launch"],
            input_schema=OpenBrowserInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_NAVIGATE],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: OpenBrowserInput = validated_input  # type: ignore
        status = self.service.start_session(browser_type=inp.browser_type)
        if inp.url:
            self.service.open_url(inp.url)
            status = self.service.get_status()
        return status.model_dump()


# 2. Open URL Tool
class OpenUrlInput(BaseModel):
    """Input parameters for OpenUrlTool."""

    url: str = Field(description="Target web URL string (e.g. 'https://youtube.com')")


class OpenUrlTool(BaseTool):
    """Tool navigating active browser tab to target URL."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.open_url",
            name="open_url",
            display_name="Open Web URL",
            description="Navigates active browser tab to a specified web URL.",
            category=ToolCategory.MEDIA,
            tags=["browser", "url", "navigate", "web"],
            input_schema=OpenUrlInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.BROWSER_NAVIGATE],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: OpenUrlInput = validated_input  # type: ignore
        res = self.service.open_url(inp.url)
        return res.model_dump()


# 3. Browser Status Tool
class BrowserStatusInput(BaseModel):
    """Input parameters for BrowserStatusTool."""


class BrowserStatusTool(BaseTool):
    """Tool querying current browser session running state and tab statistics."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.status",
            name="browser_status",
            display_name="Get Browser Status",
            description="Queries current browser session status, active tab ID, and tab count.",
            category=ToolCategory.MEDIA,
            tags=["browser", "status", "session", "web"],
            input_schema=BrowserStatusInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        status = self.service.get_status()
        return status.model_dump()


# 4. Current Page Tool
class CurrentPageInput(BaseModel):
    """Input parameters for CurrentPageTool."""


class CurrentPageTool(BaseTool):
    """Tool querying active browser tab URL and title."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.current_page",
            name="current_page",
            display_name="Get Current Page",
            description="Queries title, URL, and active tab ID of current browser page.",
            category=ToolCategory.MEDIA,
            tags=["browser", "page", "current", "web"],
            input_schema=CurrentPageInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        active_tab = self.service.get_active_tab()
        if not active_tab:
            return {"active": False, "url": "", "title": ""}
        return active_tab.model_dump()


# 5. Get Title Tool
class GetTitleInput(BaseModel):
    """Input parameters for GetTitleTool."""


class GetTitleTool(BaseTool):
    """Tool querying active web page title."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.get_title",
            name="get_title",
            display_name="Get Page Title",
            description="Queries visible title of the active browser page.",
            category=ToolCategory.MEDIA,
            tags=["browser", "title", "web"],
            input_schema=GetTitleInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        active_tab = self.service.get_active_tab()
        return {
            "title": active_tab.title if active_tab else "",
            "url": active_tab.url if active_tab else "",
        }


# 6. Get Page Text Tool
class GetPageTextInput(BaseModel):
    """Input parameters for GetPageTextTool."""

    max_length: int = Field(
        default=20000,
        ge=100,
        le=100000,
        description="Maximum character length to return",
    )


class GetPageTextTool(BaseTool):
    """Tool extracting clean visible text from active web page."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.get_page_text",
            name="get_page_text",
            display_name="Get Page Text",
            description="Extracts clean visible text from active web page with length limit.",
            category=ToolCategory.MEDIA,
            tags=["browser", "text", "read", "web"],
            input_schema=GetPageTextInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: GetPageTextInput = validated_input  # type: ignore
        text, truncated = self.service.get_page_text(max_length=inp.max_length)
        active_tab = self.service.get_active_tab()
        return {
            "url": active_tab.url if active_tab else "",
            "title": active_tab.title if active_tab else "",
            "text": text,
            "length": len(text),
            "truncated": truncated,
        }


# 7. Get Page Info Tool
class GetPageInfoInput(BaseModel):
    """Input parameters for GetPageInfoTool."""


class GetPageInfoTool(BaseTool):
    """Tool querying summary metadata of current active web page."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.get_page_info",
            name="get_page_info",
            display_name="Get Page Info",
            description="Queries page URL, title, text length, and link count summary.",
            category=ToolCategory.MEDIA,
            tags=["browser", "info", "summary", "web"],
            input_schema=GetPageInfoInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        page_info = self.service.get_page_info()
        return page_info.model_dump()


# 8. Get Links Tool
class GetLinksInput(BaseModel):
    """Input parameters for GetLinksTool."""

    max_links: int = Field(
        default=50, ge=1, le=200, description="Maximum links to extract"
    )


class GetLinksTool(BaseTool):
    """Tool extracting structured hyperlinks from active web page."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.get_links",
            name="get_links",
            display_name="Get Web Links",
            description="Extracts structured hyperlinks (text and URL) from active web page.",
            category=ToolCategory.MEDIA,
            tags=["browser", "links", "urls", "web"],
            input_schema=GetLinksInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: GetLinksInput = validated_input  # type: ignore
        links = self.service.get_links(max_links=inp.max_links)
        return {"count": len(links), "links": [lnk.model_dump() for lnk in links]}


# 9. List Tabs Tool
class ListTabsInput(BaseModel):
    """Input parameters for ListTabsTool."""


class ListTabsTool(BaseTool):
    """Tool listing open browser tabs."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.list_tabs",
            name="list_tabs",
            display_name="List Browser Tabs",
            description="Lists all open browser tabs with tab IDs, titles, and URLs.",
            category=ToolCategory.MEDIA,
            tags=["browser", "tabs", "list", "web"],
            input_schema=ListTabsInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_TABS],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        tabs = self.service.list_tabs()
        return {"tab_count": len(tabs), "tabs": [t.model_dump() for t in tabs]}


# 10. Active Tab Tool
class ActiveTabInput(BaseModel):
    """Input parameters for ActiveTabTool."""


class ActiveTabTool(BaseTool):
    """Tool querying active browser tab details."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.active_tab",
            name="active_tab",
            display_name="Get Active Tab",
            description="Queries details of currently active browser tab.",
            category=ToolCategory.MEDIA,
            tags=["browser", "tab", "active", "web"],
            input_schema=ActiveTabInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_TABS],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        tab = self.service.get_active_tab()
        return tab.model_dump() if tab else {"active": False}


# 11. New Tab Tool
class NewTabInput(BaseModel):
    """Input parameters for NewTabTool."""

    url: str | None = Field(
        default=None, description="Optional initial URL for new tab"
    )


class NewTabTool(BaseTool):
    """Tool creating a new tab with optional URL."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.new_tab",
            name="new_tab",
            display_name="New Tab",
            description="Creates a new browser tab with optional initial URL.",
            category=ToolCategory.MEDIA,
            tags=["browser", "tab", "new", "web"],
            input_schema=NewTabInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.BROWSER_TABS],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: NewTabInput = validated_input  # type: ignore
        tab = self.service.new_tab(url=inp.url)
        return tab.model_dump() if tab else {"created": False}


# 12. Switch Tab Tool
class SwitchTabInput(BaseModel):
    """Input parameters for SwitchTabTool."""

    tab_id: str = Field(description="Tab ID string to activate")


class SwitchTabTool(BaseTool):
    """Tool switching active browser tab by tab ID."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.switch_tab",
            name="switch_tab",
            display_name="Switch Tab",
            description="Switches currently active browser tab by tab ID.",
            category=ToolCategory.MEDIA,
            tags=["browser", "tab", "switch", "web"],
            input_schema=SwitchTabInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.BROWSER_TABS],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: SwitchTabInput = validated_input  # type: ignore
        switched = self.service.switch_tab(inp.tab_id)
        return {"switched": switched, "tab_id": inp.tab_id}


# 13. Close Tab Tool
class CloseTabInput(BaseModel):
    """Input parameters for CloseTabTool."""

    tab_id: str = Field(description="Tab ID string to close")


class CloseTabTool(BaseTool):
    """Tool closing a specific browser tab by tab ID."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.close_tab",
            name="close_tab",
            display_name="Close Tab",
            description="Closes a specific browser tab by tab ID.",
            category=ToolCategory.MEDIA,
            tags=["browser", "tab", "close", "web"],
            input_schema=CloseTabInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.BROWSER_TABS],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CloseTabInput = validated_input  # type: ignore
        closed = self.service.close_tab(inp.tab_id)
        return {"closed": closed, "tab_id": inp.tab_id}


# 14. Browser Back Tool
class BrowserBackInput(BaseModel):
    """Input parameters for BrowserBackTool."""


class BrowserBackTool(BaseTool):
    """Tool navigating back in browser history."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.back",
            name="back",
            display_name="Browser Back",
            description="Navigates back in active tab browser history.",
            category=ToolCategory.MEDIA,
            tags=["browser", "back", "navigate", "web"],
            input_schema=BrowserBackInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_NAVIGATE],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        res = self.service.go_back()
        return res.model_dump()


# 15. Browser Forward Tool
class BrowserForwardInput(BaseModel):
    """Input parameters for BrowserForwardTool."""


class BrowserForwardTool(BaseTool):
    """Tool navigating forward in browser history."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.forward",
            name="forward",
            display_name="Browser Forward",
            description="Navigates forward in active tab browser history.",
            category=ToolCategory.MEDIA,
            tags=["browser", "forward", "navigate", "web"],
            input_schema=BrowserForwardInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_NAVIGATE],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        res = self.service.go_forward()
        return res.model_dump()


# 16. Browser Reload Tool
class BrowserReloadInput(BaseModel):
    """Input parameters for BrowserReloadTool."""


class BrowserReloadTool(BaseTool):
    """Tool reloading active web page."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.reload",
            name="reload",
            display_name="Reload Page",
            description="Reloads the currently active web page.",
            category=ToolCategory.MEDIA,
            tags=["browser", "reload", "refresh", "web"],
            input_schema=BrowserReloadInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_NAVIGATE],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        res = self.service.reload_page()
        return res.model_dump()


# 17. Focus Browser Tool
class FocusBrowserInput(BaseModel):
    """Input parameters for FocusBrowserTool."""


class FocusBrowserTool(BaseTool):
    """Tool bringing browser window to foreground."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.focus",
            name="focus_browser",
            display_name="Focus Browser",
            description="Brings active browser window to foreground.",
            category=ToolCategory.MEDIA,
            tags=["browser", "focus", "window", "web"],
            input_schema=FocusBrowserInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.BROWSER_READ],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        focused = self.service.focus_browser()
        return {"focused": focused}


# 18. Browser Search Tool
class BrowserSearchInput(BaseModel):
    """Input parameters for BrowserSearchTool."""

    query: str = Field(
        description="Search query string (e.g. 'latest Python 3.12 features')"
    )


class BrowserSearchTool(BaseTool):
    """Tool executing web search query on configured search engine."""

    def __init__(self, service: BrowserService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="browser.search",
            name="search",
            display_name="Web Search",
            description="Executes a web search query on the configured search engine.",
            category=ToolCategory.MEDIA,
            tags=["browser", "search", "query", "web"],
            input_schema=BrowserSearchInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.BROWSER_SEARCH],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or BrowserService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: BrowserSearchInput = validated_input  # type: ignore
        res = self.service.search(inp.query)
        return res.model_dump()
