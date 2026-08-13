"""Concrete ToolExecutor implementation executing the 10-step security & execution pipeline."""

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.tools.events.tool_events import (
    ToolExecutionAuthorizationDenied,
    ToolExecutionAuthorizationRequired,
    ToolExecutionCancelled,
    ToolExecutionCompleted,
    ToolExecutionFailed,
    ToolExecutionRetrying,
    ToolExecutionStarted,
    ToolExecutionTimedOut,
)
from app.tools.execution.execution_context import ExecutionContext
from app.tools.execution.execution_metrics import ExecutionMetrics
from app.tools.execution.execution_tracker import ExecutionTracker
from app.tools.execution.executor_interface import IToolExecutor
from app.tools.execution.result_normalizer import (
    ResultNormalizer,
    SensitiveDataSanitizer,
)
from app.tools.execution.retry_policy import RetryPolicy
from app.tools.models.command import Command, CommandSource, CommandState
from app.tools.models.errors import ToolErrorCode
from app.tools.models.request import ToolRequest
from app.tools.models.result import ToolResult
from app.tools.registry.tool_registry import ToolRegistry
from app.tools.security.authorization_provider import (
    AuthorizationStatus,
    DevAuthorizationProvider,
    IAuthorizationProvider,
)


class ToolExecutor(BaseService, IToolExecutor):
    """Central Tool Execution Engine coordinating resolution, validation, authorization, execution, and metrics."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        event_bus: EventBus | None = None,
        auth_provider: IAuthorizationProvider | None = None,
        tracker: ExecutionTracker | None = None,
        metrics: ExecutionMetrics | None = None,
        default_timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(name="ToolExecutor", is_critical=False)
        self.registry = registry or ToolRegistry()
        self.event_bus = event_bus or EventBus()
        self.auth_provider = auth_provider or DevAuthorizationProvider()
        self.tracker = tracker or ExecutionTracker()
        self.metrics = metrics or ExecutionMetrics()
        self.default_timeout_seconds = default_timeout_seconds
        self._thread_pool: ThreadPoolExecutor | None = None

    def _do_initialize(self) -> None:
        """Initialize executor pool resources."""
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="ToolExecWorker"
        )
        logger.info("ToolExecutor initialized.")

    def _do_start(self) -> None:
        """Start ToolExecutor service."""
        logger.info("ToolExecutor started.")

    def _do_stop(self) -> None:
        """Shutdown thread pool executor."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
            self._thread_pool = None
        logger.info("ToolExecutor stopped.")

    def execute_command(self, command: Command) -> ToolResult:
        """Execute structured Command model."""
        return self.execute(
            tool_id=command.tool_name,
            arguments=command.arguments,
            command_id=command.command_id,
            source=command.source,
            timeout_seconds=command.timeout_seconds,
            correlation_id=command.correlation_id,
        )

    def execute_request(self, request: ToolRequest) -> ToolResult:
        """Execute raw ToolRequest model."""
        return self.execute(
            tool_id=request.tool_id,
            arguments=request.arguments,
            command_id=request.request_id,
            source=CommandSource.USER,
        )

    def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        command_id: str = "",
        source: CommandSource = CommandSource.USER,
        timeout_seconds: float | None = None,
        correlation_id: str = "",
    ) -> ToolResult:
        """Pipeline execution entrypoint handling all 10 stages.

        Args:
            tool_id: Target tool identifier.
            arguments: Raw input parameters dictionary.
            command_id: Optional correlation command ID.
            source: CommandSource origin.
            timeout_seconds: Execution timeout override.
            correlation_id: Correlation tracking ID.

        Returns:
            ToolResult: Standardized execution result.
        """
        start_time = time.time()

        # Step 1: Validate Request
        if not tool_id or not isinstance(tool_id, str):
            return ToolResult.fail(
                tool_id=tool_id or "unknown",
                command_id=command_id,
                error="Invalid request: Tool ID is required.",
                error_code=ToolErrorCode.INVALID_INPUT,
            )

        # Step 2: Tool Resolution
        tool = self.registry.get_tool(tool_id)
        if not tool:
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Tool '{tool_id}' is not registered.",
                error_code=ToolErrorCode.TOOL_NOT_FOUND,
            )

        if not tool.metadata.is_enabled:
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Tool '{tool_id}' is disabled.",
                error_code=ToolErrorCode.TOOL_DISABLED,
            )

        # Step 3: Input Validation
        try:
            tool.validate_input(arguments)
        except Exception as exc:  # noqa: BLE001
            duration = round(time.time() - start_time, 4)
            return ResultNormalizer.normalize_exception(
                tool_id, command_id, exc, duration
            )

        # Step 4: Risk & Permission Authorization Check
        auth_res = self.auth_provider.authorize_execution(tool.metadata, source=source)
        if auth_res.status == AuthorizationStatus.DENIED:
            self.event_bus.publish(
                ToolExecutionAuthorizationDenied(
                    tool_id=tool_id,
                    command_id=command_id,
                    reason=auth_res.reason,
                )
            )
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Authorization denied: {auth_res.reason}",
                error_code=ToolErrorCode.PERMISSION_DENIED,
            )

        if auth_res.status == AuthorizationStatus.CONFIRMATION_REQUIRED:
            self.event_bus.publish(
                ToolExecutionAuthorizationRequired(
                    tool_id=tool_id,
                    command_id=command_id,
                    risk_level=tool.metadata.risk_level.value,
                )
            )
            return ToolResult.fail(
                tool_id=tool_id,
                command_id=command_id,
                error=f"Authorization required: {auth_res.reason}",
                error_code=ToolErrorCode.AUTHORIZATION_REQUIRED,
            )

        # Step 5: Execution Context Setup
        effective_timeout = (
            timeout_seconds
            if timeout_seconds and timeout_seconds > 0
            else tool.metadata.timeout_seconds or self.default_timeout_seconds
        )

        context = ExecutionContext(
            command_id=command_id,
            tool_id=tool_id,
            correlation_id=correlation_id,
            source=source,
            risk_level=tool.metadata.risk_level,
            timeout_seconds=effective_timeout,
            max_retries=tool.metadata.max_retries,
            state=CommandState.EXECUTING,
        )

        self.tracker.register_execution(context)
        self.event_bus.publish(
            ToolExecutionStarted(
                tool_id=tool_id,
                command_id=command_id,
                execution_id=context.execution_id,
            )
        )

        # Log sanitized input payload
        sanitized_args = SensitiveDataSanitizer.sanitize(arguments)
        logger.info(
            f"ToolExecutor [{context.execution_id}]: Executing '{tool_id}' (Timeout: {effective_timeout}s, Arguments: {sanitized_args})."
        )

        # Step 6: Execute with Retry Engine
        result = self._execute_with_retry(tool, arguments, context)

        # Step 7: Record Metrics & History, Publish Completion/Failure Events
        self.metrics.record_execution(result, retries=context.retry_attempt)
        self.tracker.complete_execution(result)

        if result.success:
            self.event_bus.publish(
                ToolExecutionCompleted(
                    tool_id=tool_id,
                    command_id=command_id,
                    execution_id=context.execution_id,
                    duration_seconds=result.execution_duration,
                )
            )
        elif result.error_code == ToolErrorCode.TIMEOUT:
            self.event_bus.publish(
                ToolExecutionTimedOut(
                    tool_id=tool_id,
                    command_id=command_id,
                    execution_id=context.execution_id,
                    timeout_seconds=effective_timeout,
                )
            )
        elif result.error_code == ToolErrorCode.CANCELLED:
            self.event_bus.publish(
                ToolExecutionCancelled(
                    tool_id=tool_id,
                    command_id=command_id,
                )
            )
        else:
            self.event_bus.publish(
                ToolExecutionFailed(
                    tool_id=tool_id,
                    command_id=command_id,
                    error_message=result.error or "Execution failed.",
                    error_code=(
                        result.error_code.value
                        if result.error_code
                        else "EXECUTION_FAILED"
                    ),
                )
            )

        return result

    def _execute_with_retry(
        self,
        tool: Any,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Internal execution worker with timeout enforcement and retry loop."""
        attempts = 0
        while True:
            # Check cooperative cancellation
            if context.cancellation_token.is_cancelled:
                return ToolResult.fail(
                    tool_id=context.tool_id,
                    command_id=context.command_id,
                    error=f"Cancelled: {context.cancellation_token.reason}",
                    error_code=ToolErrorCode.CANCELLED,
                )

            result = self._execute_single_attempt(tool, arguments, context)
            if result.success:
                return result

            # Evaluate retry policy
            if RetryPolicy.should_retry(tool.metadata, result.error_code, attempts):
                attempts += 1
                context.retry_attempt = attempts
                logger.warning(
                    f"ToolExecutor [{context.execution_id}]: Retrying tool '{context.tool_id}' (Attempt {attempts}/{tool.metadata.max_retries})."
                )
                self.event_bus.publish(
                    ToolExecutionRetrying(
                        tool_id=context.tool_id,
                        command_id=context.command_id,
                        execution_id=context.execution_id,
                        attempt=attempts,
                        max_retries=tool.metadata.max_retries,
                    )
                )
                time.sleep(0.05 * attempts)
                continue

            return result

    def _execute_single_attempt(
        self,
        tool: Any,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Execute a single tool invocation attempt wrapped in timeout handling."""
        start_t = time.time()
        pool = self._thread_pool or ThreadPoolExecutor(max_workers=1)

        try:
            future = pool.submit(tool.execute, arguments, context.command_id)
            res: ToolResult = future.result(timeout=context.timeout_seconds)
            res.execution_id = context.execution_id
            return res
        except FutureTimeoutError:
            dur = round(time.time() - start_t, 4)
            return ToolResult.fail(
                tool_id=context.tool_id,
                command_id=context.command_id,
                error=f"Execution timed out after {context.timeout_seconds} seconds.",
                error_code=ToolErrorCode.TIMEOUT,
                execution_duration=dur,
            )
        except Exception as exc:  # noqa: BLE001
            dur = round(time.time() - start_t, 4)
            res = ResultNormalizer.normalize_exception(
                context.tool_id, context.command_id, exc, dur
            )
            res.execution_id = context.execution_id
            return res

    def health_check(self) -> dict[str, Any]:
        """Collect executor diagnostic health state."""
        data = super().health_check()
        data["active_executions"] = self.tracker.active_count
        data["metrics"] = self.metrics.get_metrics_summary()
        return data
