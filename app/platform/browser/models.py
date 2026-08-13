"""Pydantic data models for browser tabs, status, navigation, and web page content representations."""

from pydantic import BaseModel, Field


class BrowserTab(BaseModel):
    """Model representing an active browser tab."""

    tab_id: str = Field(description="Unique tab identifier string")
    title: str = Field(default="", description="Web page title")
    url: str = Field(default="", description="Active URL string")
    index: int = Field(default=0, description="Tab index position")
    active: bool = Field(default=False, description="True if currently active tab")


class BrowserStatus(BaseModel):
    """Model representing running state and metadata of Friday's browser session."""

    is_running: bool = Field(
        default=False, description="True if browser session is active"
    )
    browser_type: str = Field(
        default="chrome", description="Browser engine type (chrome, edge)"
    )
    tab_count: int = Field(default=0, description="Total number of open tabs")
    active_tab_id: str | None = Field(default=None, description="ID of active tab")
    session_id: str = Field(default="", description="Unique session ID")
    current_url: str = Field(default="", description="Current active URL")
    current_title: str = Field(default="", description="Current active page title")


class PageLink(BaseModel):
    """Model representing a hyperlink extracted from a web page."""

    text: str = Field(description="Visible anchor link text")
    url: str = Field(description="Target URL string")


class PageInfo(BaseModel):
    """Model representing visible content and metadata of a web page."""

    url: str = Field(description="Page URL string")
    title: str = Field(description="Page title string")
    text_length: int = Field(
        default=0, description="Length of visible page text in characters"
    )
    link_count: int = Field(default=0, description="Count of extracted hyperlinks")
    truncated: bool = Field(
        default=False, description="True if page text exceeded length limit"
    )


class NavigationResult(BaseModel):
    """Output result model for browser navigation operations."""

    success: bool = Field(description="True if navigation succeeded")
    url: str = Field(default="", description="Final navigated URL")
    title: str = Field(default="", description="Page title")
    tab_id: str = Field(default="", description="Tab ID navigated")
    error_message: str | None = Field(
        default=None, description="Error reason if navigation failed"
    )
