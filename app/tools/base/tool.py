"""Abstract Base Tool interface for all Friday AI Assistant capabilities."""

from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.logging import logger
from app.services.base.service_interface import BaseService
from app.tools.base.lifecycle import ToolState
from app.tools.base.metadata import ToolMetadata
from app.tools.models.errors import ToolErrorCode, ToolExecutionError
from app.tools.models.result import ToolResult


class BaseTool(BaseService):
    """Abstract Base Class enforcing standard contracts for all system and plugin tools."""

    def __init__(self, metadata: ToolMetadata) -> None:
        super().__init__(name=f"Tool_{metadata.tool_id}", is_critical=False)
        self._tool_metadata = metadata
        self._tool_state = ToolState.REGISTERED

    @property
    def metadata(self) -> ToolMetadata:
        """Get strongly typed tool metadata."""
        return self._tool_metadata

    @property
    def tool_id(self) -> str:
        """Get unique tool identifier."""
        return self._tool_metadata.tool_id

    @property
    def tool_state(self) -> ToolState:
        """Get current tool lifecycle state."""
        return self._tool_state

    def validate_input(self, input_data: dict[str, Any]) -> BaseModel:
        """Validate input payload dictionary against tool's Pydantic input schema.

        Args:
            input_data: Raw input arguments dictionary.

        Returns:
            BaseModel: Validated Pydantic input model.

        Raises:
            ToolExecutionError: If validation fails.
        """
        if not self._tool_metadata.input_schema:
            return BaseModel()

        try:
            return self._tool_metadata.input_schema.model_validate(input_data)
        except ValidationError as exc:
            logger.warning(f"Tool '{self.tool_id}' input validation failed: {exc}")
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Input validation failed for tool '{self.tool_id}': {exc}",
                tool_id=self.tool_id,
            ) from exc

    def _do_initialize(self) -> None:
        """Initialize tool resources."""
        self._tool_state = ToolState.INITIALIZED

    def _do_start(self) -> None:
        """Set tool state to READY."""
        self._tool_state = ToolState.READY

    def _do_stop(self) -> None:
        """Set tool state to SHUTDOWN."""
        self._tool_state = ToolState.SHUTDOWN

    @abstractmethod
    def run_tool(self, validated_input: BaseModel, command_id: str = "") -> Any:
        """Execute concrete tool logic with validated input model. Implemented by concrete tools."""

    def execute(self, input_data: dict[str, Any], command_id: str = "") -> ToolResult:
        """Execute tool wrapper performing input validation, timer tracking, and result format.

        Args:
            input_data: Raw argument dictionary.
            command_id: Optional correlation command ID.

        Returns:
            ToolResult: Standardized tool execution result object.
        """
        if not self._tool_metadata.is_enabled:
            return ToolResult.fail(
                tool_id=self.tool_id,
                command_id=command_id,
                error="Tool is currently disabled.",
                error_code=ToolErrorCode.TOOL_DISABLED,
            )

        import time

        start_time = time.time()

        try:
            validated_input = self.validate_input(input_data)
            result_data = self.run_tool(validated_input, command_id=command_id)
            duration = round(time.time() - start_time, 4)

            return ToolResult.ok(
                tool_id=self.tool_id,
                command_id=command_id,
                result_data=result_data,
                execution_duration=duration,
            )
        except ToolExecutionError as exc:
            duration = round(time.time() - start_time, 4)
            return ToolResult.fail(
                tool_id=self.tool_id,
                command_id=command_id,
                error=exc.message,
                error_code=exc.error_code,
                execution_duration=duration,
            )
        except Exception as exc:  # noqa: BLE001
            duration = round(time.time() - start_time, 4)
            logger.error(f"Tool '{self.tool_id}' execution exception: {exc}")
            return ToolResult.fail(
                tool_id=self.tool_id,
                command_id=command_id,
                error=str(exc),
                error_code=ToolErrorCode.EXECUTION_FAILED,
                execution_duration=duration,
            )

    def health_check(self) -> dict[str, Any]:
        """Collect diagnostic health report data."""
        data = super().health_check()
        data["tool_id"] = self.tool_id
        data["tool_state"] = self.tool_state.value
        data["is_enabled"] = self.metadata.is_enabled
        data["risk_level"] = self.metadata.risk_level.value
        return data
