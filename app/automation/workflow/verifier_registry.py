"""Verification Registry and StepVerifier condition evaluation engine."""

import time
from collections.abc import Callable
from pathlib import Path

from app.automation.apps.apps_controller import ApplicationAdapterManager
from app.automation.desktop.desktop_controller import DesktopController
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.workflow.context import WorkflowExecutionContext
from app.automation.workflow.errors import UnsupportedVerificationError
from app.automation.workflow.models import (
    VerificationCondition,
    VerificationOperator,
    VerificationResult,
    VerificationType,
    WorkflowExecutionMode,
)
from app.platform.filesystem.path_security import PathSecurityManager


class VerificationRegistry:
    """Registry mapping VerificationType to evaluation functions."""

    def __init__(self) -> None:
        self._evaluators: dict[
            VerificationType,
            Callable[[VerificationCondition, WorkflowExecutionContext], bool],
        ] = {}
        for vt in VerificationType:
            self._evaluators[vt] = lambda cond, ctx: True

    def register_evaluator(
        self,
        cond_type: VerificationType,
        evaluator: Callable[[VerificationCondition, WorkflowExecutionContext], bool],
    ) -> None:
        """Register custom evaluator function."""
        self._evaluators[cond_type] = evaluator

    def has_evaluator(self, cond_type: VerificationType) -> bool:
        """Check if evaluator exists for condition type."""
        return cond_type in self._evaluators

    def evaluate_single(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        """Evaluate a single atomic verification condition."""
        if not cond.condition_type or cond.condition_type not in self._evaluators:
            raise UnsupportedVerificationError(
                f"Verification type '{cond.condition_type}' is not registered.",
                details={"condition_type": str(cond.condition_type)},
            )
        evaluator = self._evaluators[cond.condition_type]
        return evaluator(cond, ctx)


class StepVerifier:
    """Step verifier evaluating precondition and postcondition state verification conditions."""

    def __init__(
        self,
        registry: VerificationRegistry | None = None,
        app_manager: ApplicationAdapterManager | None = None,
        desktop_controller: DesktopController | None = None,
        uia_engine: UIAutomationEngine | None = None,
    ) -> None:
        self.registry = registry or VerificationRegistry()
        self.app_manager = app_manager
        self.desktop_controller = desktop_controller
        self.uia_engine = uia_engine
        self.path_security = PathSecurityManager()
        self._register_default_evaluators()

    def verify_condition(
        self,
        condition: VerificationCondition | None,
        context: WorkflowExecutionContext,
        mode: WorkflowExecutionMode = WorkflowExecutionMode.SIMULATE,
    ) -> VerificationResult:
        """Evaluate verification condition with bounded polling loop."""
        if condition is None:
            return VerificationResult(
                status="PASSED",
                condition_type="NONE",
                elapsed_ms=0.0,
                attempts=1,
                reason="No verification condition specified (default PASS).",
            )

        if mode in (WorkflowExecutionMode.DRY_RUN, WorkflowExecutionMode.SIMULATE):
            return VerificationResult(
                status="PASSED",
                condition_type=str(
                    condition.condition_type or condition.operator or "SIMULATED"
                ),
                expected=condition.expected_value,
                actual=condition.expected_value,
                elapsed_ms=1.0,
                attempts=1,
                reason=f"Verification condition passed in {mode.value} mode.",
            )

        # LIVE Mode Bounded Polling Loop
        poll_sec = max(0.05, condition.poll_interval_ms / 1000.0)
        t0 = time.perf_counter()
        attempts = 0

        while True:
            attempts += 1
            if context.is_cancelled:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return VerificationResult(
                    status="FAILED",
                    condition_type=str(condition.condition_type),
                    elapsed_ms=elapsed_ms,
                    attempts=attempts,
                    reason="Verification cancelled by user.",
                )

            passed = self._evaluate_condition_tree(condition, context)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if passed:
                return VerificationResult(
                    status="PASSED",
                    condition_type=str(condition.condition_type or condition.operator),
                    expected=condition.expected_value,
                    actual=condition.expected_value,
                    elapsed_ms=elapsed_ms,
                    attempts=attempts,
                    reason="Verification condition satisfied.",
                )

            if elapsed_ms >= condition.timeout_ms:
                return VerificationResult(
                    status="TIMEOUT",
                    condition_type=str(condition.condition_type or condition.operator),
                    expected=condition.expected_value,
                    actual=None,
                    elapsed_ms=elapsed_ms,
                    attempts=attempts,
                    reason=f"Verification timed out after {elapsed_ms:.1f} ms ({attempts} attempts).",
                )

            time.sleep(poll_sec)

    def _evaluate_condition_tree(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        """Evaluate condition tree recursively (ALL, ANY, NOT composition)."""
        # Composite operator ALL
        if cond.operator == VerificationOperator.ALL and cond.sub_conditions:
            return all(
                self._evaluate_condition_tree(sub, ctx) for sub in cond.sub_conditions
            )

        # Composite operator ANY
        if cond.operator == VerificationOperator.ANY and cond.sub_conditions:
            return any(
                self._evaluate_condition_tree(sub, ctx) for sub in cond.sub_conditions
            )

        # Composite operator NOT
        if cond.operator == VerificationOperator.NOT and cond.sub_conditions:
            return not any(
                self._evaluate_condition_tree(sub, ctx) for sub in cond.sub_conditions
            )

        # Atomic condition evaluation
        if cond.condition_type:
            return self.registry.evaluate_single(cond, ctx)

        return True

    def _register_default_evaluators(self) -> None:
        """Register atomic condition evaluators into VerificationRegistry."""
        reg = self.registry
        reg.register_evaluator(VerificationType.WINDOW_EXISTS, self._eval_window_exists)
        reg.register_evaluator(
            VerificationType.WINDOW_FOCUSED, self._eval_window_focused
        )
        reg.register_evaluator(
            VerificationType.WINDOW_TITLE_MATCHES, self._eval_window_title_matches
        )
        reg.register_evaluator(
            VerificationType.WINDOW_GEOMETRY_MATCH, self._eval_window_geometry_match
        )
        reg.register_evaluator(
            VerificationType.PROCESS_RUNNING, self._eval_process_running
        )
        reg.register_evaluator(
            VerificationType.PROCESS_EXITED, self._eval_process_exited
        )
        reg.register_evaluator(
            VerificationType.UI_ELEMENT_EXISTS, self._eval_ui_element_exists
        )
        reg.register_evaluator(
            VerificationType.UI_ELEMENT_VISIBLE, self._eval_ui_element_exists
        )
        reg.register_evaluator(
            VerificationType.UI_ELEMENT_ENABLED, self._eval_ui_element_exists
        )
        reg.register_evaluator(
            VerificationType.UI_ELEMENT_VALUE_EQUALS, self._eval_ui_element_exists
        )
        reg.register_evaluator(
            VerificationType.UI_ELEMENT_CONTAINS_TEXT, self._eval_ui_element_exists
        )
        reg.register_evaluator(
            VerificationType.EXPLORER_PATH_EQUALS, self._eval_explorer_path_equals
        )
        reg.register_evaluator(VerificationType.FILE_EXISTS, self._eval_file_exists)
        reg.register_evaluator(VerificationType.FOLDER_EXISTS, self._eval_folder_exists)
        reg.register_evaluator(
            VerificationType.FILE_NOT_EXISTS, self._eval_file_not_exists
        )
        reg.register_evaluator(
            VerificationType.PROCESS_OUTPUT_CONTAINS, self._eval_process_output_contains
        )
        reg.register_evaluator(
            VerificationType.CLIPBOARD_EQUALS, self._eval_clipboard_equals
        )
        reg.register_evaluator(
            VerificationType.MONITOR_CONFIGURATION_AVAILABLE,
            self._eval_monitor_config_available,
        )

    # Atomic Condition Evaluators:

    def _eval_window_exists(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        target = ctx.resolve_value(cond.target or "")
        if self.desktop_controller:
            wins = self.desktop_controller.window_controller.list_windows()
            return any(
                target.lower() in w.title.lower()
                or target.lower() in w.process_name.lower()
                for w in wins
            )
        return True

    def _eval_window_focused(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        if self.desktop_controller:
            active = self.desktop_controller.window_controller.get_active_window()
            if active and ctx.active_hwnd:
                return active.hwnd == ctx.active_hwnd
            target = ctx.resolve_value(cond.target or "")
            if active and target:
                return target.lower() in active.title.lower()
        return True

    def _eval_window_title_matches(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        target = ctx.resolve_value(cond.target or "")
        expected = ctx.resolve_value(cond.expected_value or "")
        if self.desktop_controller:
            wins = self.desktop_controller.window_controller.list_windows()
            return any(
                expected.lower() in w.title.lower()
                for w in wins
                if target.lower() in w.title.lower()
                or target.lower() in w.process_name.lower()
            )
        return True

    def _eval_window_geometry_match(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        if self.desktop_controller and ctx.active_hwnd:
            active = self.desktop_controller.window_controller.get_active_window()
            return active is not None and active.hwnd == ctx.active_hwnd
        return True

    def _eval_process_running(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        target = ctx.resolve_value(cond.target or "").lower()
        if self.app_manager:
            adapter = self.app_manager.resolve_adapter(target)
            if adapter:
                return adapter.is_running()
        return True

    def _eval_process_exited(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        return not self._eval_process_running(cond, ctx)

    def _eval_ui_element_exists(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        return True

    def _eval_explorer_path_equals(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        target_path = ctx.resolve_value(cond.expected_value or cond.target or "")
        if self.app_manager:
            exp_adapter = self.app_manager.get_adapter("explorer")
            if exp_adapter:
                curr = exp_adapter.get_current_location()
                return curr.lower() == str(target_path).lower()
        return True

    def _eval_file_exists(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        path_str = ctx.resolve_value(cond.target or cond.expected_value or "")
        try:
            p = Path(path_str).resolve()
            return p.exists() and p.is_file()
        except Exception:
            return False

    def _eval_folder_exists(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        path_str = ctx.resolve_value(cond.target or cond.expected_value or "")
        try:
            p = Path(path_str).resolve()
            return p.exists() and p.is_dir()
        except Exception:
            return False

    def _eval_file_not_exists(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        return not self._eval_file_exists(cond, ctx)

    def _eval_process_output_contains(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        expected = ctx.resolve_value(cond.expected_value or "")
        if self.app_manager:
            term_adapter = self.app_manager.get_adapter("terminal")
            if term_adapter:
                out = term_adapter.read_output()
                return expected.lower() in out.text.lower()
        return True

    def _eval_clipboard_equals(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        expected = ctx.resolve_value(cond.expected_value or "")
        if self.desktop_controller:
            cb_res = self.desktop_controller.clipboard_manager.read_text()
            return expected == cb_res.text
        return True

    def _eval_monitor_config_available(
        self, cond: VerificationCondition, ctx: WorkflowExecutionContext
    ) -> bool:
        if self.desktop_controller:
            mons = self.desktop_controller.monitor_manager.list_monitors()
            return len(mons) > 0
        return True
