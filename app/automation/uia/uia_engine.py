"""Concrete implementation of the Windows UI Automation Engine service."""

import sys
import threading
import time
from typing import Any

from app.automation.errors import (
    ElementNotFoundError,
    ElementStaleError,
    UIAEngineError,
)
from app.automation.models import (
    AutomationElement,
    WindowSearchResult,
    WindowSearchStatus,
)
from app.automation.uia.control_patterns import ControlPatternManager
from app.automation.uia.diagnostics import UIAutomationDiagnostics
from app.automation.uia.element_adapter import ElementAdapter
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.element_finder_interface import IElementFinder
from app.automation.uia.metrics import UIAutomationMetrics
from app.automation.uia.tree_walker import UITreeWalker
from app.automation.uia.uia_engine_interface import IUIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver
from app.logging import logger

try:
    import pywinauto
    from pywinauto.application import Application
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_element_info import UIAElementInfo

    PYWINAUTO_AVAILABLE = True
except ImportError:
    pywinauto = None
    Application = None
    UIAWrapper = None
    UIAElementInfo = None
    PYWINAUTO_AVAILABLE = False


class UIAutomationEngine(IUIAutomationEngine):
    """Core UIA engine service providing window attachment, tree traversal, semantic search, and pattern actions."""

    def __init__(
        self,
        window_resolver: WindowResolver | None = None,
        tree_walker: UITreeWalker | None = None,
        element_finder: ElementFinder | None = None,
        metrics: UIAutomationMetrics | None = None,
        diagnostics: UIAutomationDiagnostics | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._initialized = False

        self.window_resolver = window_resolver or WindowResolver()
        self.metrics = metrics or UIAutomationMetrics()
        self.tree_walker = tree_walker or UITreeWalker()
        self.element_finder = element_finder or ElementFinder(
            tree_walker=self.tree_walker
        )
        self.diagnostics = diagnostics or UIAutomationDiagnostics(
            window_resolver=self.window_resolver, metrics=self.metrics
        )

    def is_available(self) -> bool:
        """Return True if UIA engine can operate on current platform."""
        return (
            sys.platform == "win32"
            and PYWINAUTO_AVAILABLE
            and self.window_resolver.is_available()
        )

    def initialize(self) -> bool:
        """Initialize UIA backend safely and non-invasively."""
        with self._lock:
            if self._initialized:
                return True

            if not self.is_available():
                logger.warning(
                    "UIA Engine unavailable on host system. Operating in UNAVAILABLE/DEGRADED mode."
                )
                return False

            try:
                # Test pywinauto UIA module access
                self.metrics.record_engine_init()
                self._initialized = True
                logger.info(
                    "UI Automation Engine successfully initialized with pywinauto UIA backend."
                )
                return True
            except Exception as exc:
                logger.error(f"Failed to initialize UIA Engine: {exc}")
                raise UIAEngineError("Failed to initialize UIA backend", cause=exc)

    def get_health_status(self) -> dict[str, Any]:
        """Return health status diagnostic report."""
        return self.diagnostics.get_health_report()

    def resolve_window(
        self,
        title: str | None = None,
        process_id: int | None = None,
        process_name: str | None = None,
        hwnd: int | None = None,
    ) -> WindowSearchResult:
        """Resolve top-level application window by criteria."""
        t0 = time.perf_counter()
        self.metrics.record_window_enum()
        res = self.window_resolver.resolve_window(
            title=title, process_id=process_id, process_name=process_name, hwnd=hwnd
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        self.metrics.record_element_search(
            success=(res.status == WindowSearchStatus.FOUND),
            ambiguous=(res.status == WindowSearchStatus.AMBIGUOUS),
            latency_ms=latency_ms,
        )
        return res

    def get_root_element(self, hwnd: int) -> tuple[Any, AutomationElement]:
        """Wrap native HWND into pywinauto control wrapper and domain AutomationElement."""
        if not self.is_available():
            raise UIAEngineError("UIA Engine is unavailable.")

        if not hwnd or hwnd <= 0:
            raise ElementNotFoundError(f"Invalid HWND handle: {hwnd}")

        try:
            app = Application(backend="uia").connect(handle=hwnd)
            window_wrapper = app.window(handle=hwnd)
            raw_element = window_wrapper.wrapper_object()

            domain_elem = ElementAdapter.create_automation_element(
                raw_element, depth=0, parent_id=None
            )
            domain_elem.window_handle = hwnd
            return raw_element, domain_elem
        except Exception as exc:
            safe_exc = str(exc).replace("{", "{{").replace("}", "}}")
            logger.error(f"Failed to connect to window HWND {hwnd}: {safe_exc}")
            raise ElementNotFoundError(
                f"Could not connect to window HWND {hwnd}",
                details={"hwnd": hwnd},
                cause=exc,
            )

    def get_tree_walker(self) -> UITreeWalker:
        """Return tree walker service."""
        return self.tree_walker

    def get_element_finder(self) -> IElementFinder:
        """Return element finder service."""
        return self.element_finder

    def invoke_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely execute InvokePattern on element."""
        try:
            res = ControlPatternManager.invoke(raw_element, element)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def get_element_value(
        self, raw_element: Any, element: AutomationElement
    ) -> str | None:
        """Safely read value from element via ValuePattern."""
        try:
            val = ControlPatternManager.get_value(raw_element, element)
            self.metrics.record_pattern_detection()
            return val
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def set_element_value(
        self, raw_element: Any, element: AutomationElement, value: str
    ) -> bool:
        """Safely set value on element via ValuePattern."""
        try:
            res = ControlPatternManager.set_value(raw_element, element, value)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def toggle_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely toggle element state via TogglePattern."""
        try:
            res = ControlPatternManager.toggle(raw_element, element)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def select_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely select item via SelectionItemPattern."""
        try:
            res = ControlPatternManager.select(raw_element, element)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def expand_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely expand element via ExpandCollapsePattern."""
        try:
            res = ControlPatternManager.expand(raw_element, element)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise

    def collapse_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely collapse element via ExpandCollapsePattern."""
        try:
            res = ControlPatternManager.collapse(raw_element, element)
            self.metrics.record_pattern_detection()
            return res
        except ElementStaleError:
            self.metrics.record_stale_element_error()
            raise
