"""Tool permission models and Default Deny permission validation rules."""

from enum import Enum

from pydantic import BaseModel, Field


class ToolPermission(str, Enum):
    """System permission capabilities required for tool execution."""

    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_CREATE = "filesystem.create"
    FILESYSTEM_COPY = "filesystem.copy"
    FILESYSTEM_MOVE = "filesystem.move"
    FILESYSTEM_RENAME = "filesystem.rename"
    FILESYSTEM_DELETE = "filesystem.delete"
    FILESYSTEM_SEARCH = "filesystem.search"
    PROCESS_READ = "process.read"
    PROCESS_CONTROL = "process.control"
    NETWORK_ACCESS = "network.access"
    CLIPBOARD_READ = "clipboard.read"
    CLIPBOARD_WRITE = "clipboard.write"
    SYSTEM_POWER = "system.power"
    SYSTEM_SETTINGS = "system.settings"
    BROWSER_READ = "browser.read"
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_TABS = "browser.tabs"
    BROWSER_SEARCH = "browser.search"
    AUTOMATION_READ = "automation.read"
    AUTOMATION_UI = "automation.ui"
    AUTOMATION_INPUT = "automation.input"
    AUTOMATION_WINDOW = "automation.window"
    AUTOMATION_SCREEN = "automation.screen"
    AUTOMATION_CLIPBOARD = "automation.clipboard"
    AUTOMATION_APPLICATION = "automation.application"
    AUTOMATION_TERMINAL = "automation.terminal"
    AUTOMATION_WORKFLOW = "automation.workflow"


class PermissionRequirement(BaseModel):
    """Permission requirement specification for tool execution."""

    required_permissions: list[ToolPermission] = Field(default_factory=list)
    default_deny: bool = Field(
        default=True, description="Enforce Default Deny security principle"
    )

    def validate_permissions(
        self, granted_permissions: set[ToolPermission]
    ) -> tuple[bool, list[ToolPermission]]:
        """Validate whether granted permissions satisfy requirements.

        Args:
            granted_permissions: Set of explicitly granted permissions.

        Returns:
            tuple: (is_authorized, list_of_missing_permissions)
        """
        missing = [p for p in self.required_permissions if p not in granted_permissions]
        if missing and self.default_deny:
            return False, missing
        return True, []
