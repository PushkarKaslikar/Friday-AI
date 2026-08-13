"""Central Tool Calling & Function Binding Engine implementation.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import json
import threading
import time
from typing import Any

from app.ai.tool_calling.engine_interface import IToolCallingEngine
from app.ai.tool_calling.events import (
    ToolCallExecutionCompleted,
    ToolCallExecutionFailed,
    ToolCallExecutionStarted,
    ToolCallGenerated,
    ToolCallRejected,
    ToolCallValidated,
)
from app.ai.tool_calling.metrics import ToolCallingMetrics
from app.ai.tool_calling.models import (
    ToolCall,
    ToolCallingConfiguration,
    ToolCallResult,
    ToolCallStatus,
    ToolDefinition,
)
from app.ai.tool_calling.provider_adapter import (
    DefaultToolCallAdapter,
    IToolCallAdapter,
)
from app.ai.tool_calling.schema_registry import ToolSchemaRegistry
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.tools.categories import ToolCategory
from app.tools.discovery.tool_discovery import ToolDiscoveryService
from app.tools.execution.execution_context import ExecutionContext
from app.tools.execution.result_normalizer import SensitiveDataSanitizer
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.errors import ToolExecutionError
from app.tools.registry.tool_registry import ToolRegistry


class ToolCallingEngine(BaseService, IToolCallingEngine):
    """Central engine managing schema resolution, model tool parsing, validation, Phase 2 execution delegation, and sanitized model-facing output formatting."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
        discovery_service: ToolDiscoveryService | None = None,
        schema_registry: ToolSchemaRegistry | None = None,
        adapter: IToolCallAdapter | None = None,
        metrics: ToolCallingMetrics | None = None,
    ) -> None:
        super().__init__(name="ToolCallingEngine", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.tool_registry = tool_registry or ToolRegistry(event_bus=self.event_bus)
        self.tool_executor = tool_executor or ToolExecutor(
            registry=self.tool_registry, event_bus=self.event_bus
        )
        self.discovery_service = discovery_service or ToolDiscoveryService(
            registry=self.tool_registry
        )
        self.schema_registry = schema_registry or ToolSchemaRegistry(
            tool_registry=self.tool_registry
        )
        self.adapter = adapter or DefaultToolCallAdapter()
        self.metrics = metrics or ToolCallingMetrics()

        self._lock = threading.Lock()
        self._config = self._load_configuration()
        self._last_error: str | None = None
        self._executed_call_history: set[str] = set()

    @property
    def config(self) -> ToolCallingConfiguration:
        """Active configuration settings."""
        return self._config

    def _load_configuration(self) -> ToolCallingConfiguration:
        """Load settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "tool_calling"):
                cfg = settings.tool_calling
                return ToolCallingConfiguration(
                    enabled=cfg.enabled,
                    max_tool_definitions=cfg.max_tool_definitions,
                    max_result_chars=cfg.max_result_chars,
                    duplicate_call_protection=cfg.duplicate_call_protection,
                    schema_cache_enabled=cfg.schema_cache_enabled,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"ToolCallingEngine: Failed to load config, using defaults: {exc}"
            )

        return ToolCallingConfiguration()

    def _do_initialize(self) -> None:
        """Initialize engine resources."""
        logger.info("ToolCallingEngine initialized.")

    def _do_start(self) -> None:
        """Start engine service."""
        logger.info("ToolCallingEngine started.")

    def _do_stop(self) -> None:
        """Stop engine service."""
        logger.info("ToolCallingEngine stopped.")

    def get_tool_definitions(
        self, query: str | None = None, category: str | None = None, max_tools: int = 20
    ) -> list[ToolDefinition]:
        """Retrieve canonical model-friendly ToolDefinition schemas matching optional query or category."""
        limit = min(max_tools or self._config.max_tool_definitions, 50)

        if query:
            matching_meta = self.discovery_service.search_tools(query)
            definitions = []
            for meta in matching_meta[:limit]:
                defn = self.schema_registry.get_tool_definition(meta.tool_id)
                if defn and defn.is_enabled:
                    definitions.append(defn)
            return definitions

        if category:
            try:
                cat_enum = ToolCategory(category)
                matching_meta = self.discovery_service.find_by_category(cat_enum)
                definitions = []
                for meta in matching_meta[:limit]:
                    defn = self.schema_registry.get_tool_definition(meta.tool_id)
                    if defn and defn.is_enabled:
                        definitions.append(defn)
                return definitions
            except Exception:  # noqa: BLE001, S110
                pass

        all_defns = self.schema_registry.generate_all_definitions(enabled_only=True)
        return all_defns[:limit]

    def parse_tool_call(self, provider_output: Any) -> ToolCall | None:
        """Parse raw model output into canonical ToolCall model."""
        call = self.adapter.parse(provider_output)
        if call:
            self.metrics.record_call_generated()
            self.event_bus.publish(
                ToolCallGenerated(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                )
            )
        return call

    def validate_tool_call(
        self, call: ToolCall
    ) -> tuple[bool, ToolCallStatus, str | None]:
        """Validate tool existence, enabled state, required arguments, and types."""
        tool_name = call.tool_name

        # 1. Tool existence check
        if not self.tool_registry.has_tool(tool_name):
            err_msg = f"Unknown tool '{tool_name}' requested. Tool is not registered in Friday."
            self.metrics.record_validation_result(False, "UNKNOWN_TOOL")
            self.event_bus.publish(
                ToolCallRejected(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    reason=err_msg,
                    status="UNKNOWN_TOOL",
                )
            )
            return False, ToolCallStatus.UNKNOWN_TOOL, err_msg

        tool = self.tool_registry.get_tool(tool_name)
        if not tool or not tool.metadata.is_enabled:
            err_msg = f"Tool '{tool_name}' is currently disabled."
            self.metrics.record_validation_result(False, "REJECTED")
            self.event_bus.publish(
                ToolCallRejected(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    reason=err_msg,
                    status="REJECTED",
                )
            )
            return False, ToolCallStatus.REJECTED, err_msg

        # 2. Argument schema validation
        try:
            tool.validate_input(call.arguments)
        except ToolExecutionError as exc:
            err_msg = f"Invalid arguments for tool '{tool_name}': {exc.message}"
            self.metrics.record_validation_result(False, "INVALID_ARGUMENTS")
            self.event_bus.publish(
                ToolCallRejected(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    reason=err_msg,
                    status="INVALID_ARGUMENTS",
                )
            )
            return False, ToolCallStatus.INVALID_ARGUMENTS, err_msg

        self.metrics.record_validation_result(True, "SUCCESS")
        self.event_bus.publish(
            ToolCallValidated(call_id=call.call_id, tool_name=tool_name, is_valid=True)
        )
        return True, ToolCallStatus.SUCCESS, None

    def execute_tool_call(
        self, call: ToolCall, context: ExecutionContext | None = None
    ) -> ToolCallResult:
        """Validate and delegate tool execution to Phase 2 ToolExecutor engine."""
        t_start = time.time()

        # 1. Validation boundary
        is_valid, val_status, val_error = self.validate_tool_call(call)
        if not is_valid:
            duration_ms = (time.time() - t_start) * 1000.0
            return ToolCallResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                status=val_status,
                error=val_error,
                duration_ms=round(duration_ms, 2),
                model_facing_output=self._format_model_output(
                    call.call_id, call.tool_name, val_status.value, None, val_error
                ),
            )

        # 2. Duplicate call protection (if enabled)
        call_hash = f"{call.tool_name}:{json.dumps(call.arguments, sort_keys=True)}"
        if (
            self._config.duplicate_call_protection
            and call_hash in self._executed_call_history
        ):
            logger.info(
                f"ToolCallingEngine: Duplicate tool call detected for '{call.tool_name}'."
            )

        self.event_bus.publish(
            ToolCallExecutionStarted(call_id=call.call_id, tool_name=call.tool_name)
        )

        # 3. Delegate to Phase 2 ToolExecutor
        try:
            exec_result = self.tool_executor.execute(
                tool_id=call.tool_name,
                arguments=call.arguments,
                correlation_id=call.call_id,
                timeout_seconds=call.arguments.get("_timeout"),
            )

            duration_ms = (time.time() - t_start) * 1000.0
            self._executed_call_history.add(call_hash)

            # 4. Map execution status
            if exec_result.is_success:
                call_status = ToolCallStatus.SUCCESS
            elif exec_result.error and "AUTHORIZATION_REQUIRED" in str(
                exec_result.error.code
            ):
                call_status = ToolCallStatus.AUTHORIZATION_REQUIRED
            elif exec_result.error and "AUTHORIZATION_DENIED" in str(
                exec_result.error.code
            ):
                call_status = ToolCallStatus.AUTHORIZATION_DENIED
            else:
                call_status = ToolCallStatus.FAILED

            # 5. Sanitize sensitive credential data
            raw_res = exec_result.result or {}
            sanitized_res = SensitiveDataSanitizer.sanitize_dict(raw_res)

            # 6. Format prompt injection safe model-facing output
            err_text = exec_result.error.message if exec_result.error else None
            model_output = self._format_model_output(
                call.call_id, call.tool_name, call_status.value, sanitized_res, err_text
            )

            self.metrics.record_execution_result(call_status.value, duration_ms)

            if call_status == ToolCallStatus.SUCCESS:
                self.event_bus.publish(
                    ToolCallExecutionCompleted(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        status="SUCCESS",
                        duration_ms=duration_ms,
                    )
                )
            else:
                self.event_bus.publish(
                    ToolCallExecutionFailed(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        error_message=err_text or call_status.value,
                    )
                )

            return ToolCallResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                status=call_status,
                result=raw_res,
                sanitized_result=sanitized_res,
                error=err_text,
                duration_ms=round(duration_ms, 2),
                execution_id=exec_result.result_id,
                model_facing_output=model_output,
            )

        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.time() - t_start) * 1000.0
            err_msg = str(exc)
            logger.error(
                f"ToolCallingEngine: Execution exception for '{call.tool_name}': {err_msg}"
            )
            self.metrics.record_execution_result("FAILED", duration_ms)
            self.event_bus.publish(
                ToolCallExecutionFailed(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    error_message=err_msg,
                )
            )
            return ToolCallResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                status=ToolCallStatus.FAILED,
                error=err_msg,
                duration_ms=round(duration_ms, 2),
                model_facing_output=self._format_model_output(
                    call.call_id, call.tool_name, "FAILED", None, err_msg
                ),
            )

    def execute_multiple_tool_calls(
        self, calls: list[ToolCall], sequential: bool = True
    ) -> list[ToolCallResult]:
        """Execute sequence of tool calls sequentially."""
        results: list[ToolCallResult] = []
        for call in calls:
            res = self.execute_tool_call(call)
            results.append(res)
            # Stop sequence if a call fails fatally or requires user confirmation
            if res.status in (
                ToolCallStatus.AUTHORIZATION_REQUIRED,
                ToolCallStatus.AUTHORIZATION_DENIED,
                ToolCallStatus.UNKNOWN_TOOL,
            ):
                logger.info(
                    f"ToolCallingEngine: Stopping call sequence at '{call.tool_name}' due to status {res.status.value}."
                )
                break
        return results

    def _format_model_output(
        self,
        call_id: str,
        tool_name: str,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str:
        """Format prompt-injection-safe bounded model-facing result tags."""
        payload: dict[str, Any] = {"status": status}
        if result:
            payload["result"] = result
        if error:
            payload["error"] = error

        serialized = json.dumps(payload, default=str)
        max_chars = self._config.max_result_chars
        if len(serialized) > max_chars:
            serialized = (
                serialized[:max_chars] + f"... [Truncated at {max_chars} chars]"
            )

        return f'<TOOL_RESULT call_id="{call_id}" tool_name="{tool_name}" status="{status}">\n{serialized}\n</TOOL_RESULT>'

    def get_health_report(self) -> dict[str, Any]:
        """Generate comprehensive diagnostic health report."""
        return {
            "status": (
                "HEALTHY"
                if self._config.enabled and not self._last_error
                else "DEGRADED"
            ),
            "subsystem": "Tool Calling & Function Binding Engine",
            "enabled": self._config.enabled,
            "max_tool_definitions": self._config.max_tool_definitions,
            "max_result_chars": self._config.max_result_chars,
            "duplicate_call_protection": self._config.duplicate_call_protection,
            "schema_cache_enabled": self._config.schema_cache_enabled,
            "registered_tools_count": self.tool_registry.registered_count,
            "last_error": self._last_error,
            "metrics": self.metrics.get_metrics_snapshot(),
        }

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
