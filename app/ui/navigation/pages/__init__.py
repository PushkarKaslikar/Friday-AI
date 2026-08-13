"""Navigation pages package."""

from app.ui.navigation.pages.assistant_page import AssistantPage
from app.ui.navigation.pages.automation_page import AutomationPage
from app.ui.navigation.pages.base_page import BasePage
from app.ui.navigation.pages.diagnostics_page import DiagnosticsPage
from app.ui.navigation.pages.home_page import HomePage
from app.ui.navigation.pages.logs_page import LogsPage
from app.ui.navigation.pages.memory_page import MemoryPage
from app.ui.navigation.pages.plugins_page import PluginsPage

__all__ = [
    "AssistantPage",
    "AutomationPage",
    "BasePage",
    "DiagnosticsPage",
    "HomePage",
    "LogsPage",
    "MemoryPage",
    "PluginsPage",
]
