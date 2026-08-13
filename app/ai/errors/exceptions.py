"""Exception hierarchy for Local LLM Runtime.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

from typing import Any

from app.exceptions.base import FridayBaseException


class LLMBaseException(FridayBaseException):
    """Base exception class for all Local LLM Runtime errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="LLM_ERROR", details=details)


class ModelNotConfiguredError(LLMBaseException):
    """Raised when LLM settings or model paths are missing."""

    def __init__(
        self, message: str = "LLM model path or provider is not configured."
    ) -> None:
        super().__init__(message=message)


class ModelNotFoundError(LLMBaseException):
    """Raised when configured GGUF model file cannot be found on local filesystem."""

    def __init__(self, model_path: str) -> None:
        super().__init__(
            message=f"Local LLM model file not found at path: '{model_path}'",
            details={"model_path": model_path},
        )


class ModelLoadError(LLMBaseException):
    """Raised when local model fails to load into memory."""

    def __init__(self, model_path: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to load local LLM model from '{model_path}': {reason}",
            details={"model_path": model_path, "reason": reason},
        )


class ModelNotReadyError(LLMBaseException):
    """Raised when inference is attempted before model is loaded."""

    def __init__(self, state: str = "UNINITIALIZED") -> None:
        super().__init__(
            message=f"Local LLM model is not ready for inference (current state: '{state}').",
            details={"state": state},
        )


class ModelInferenceError(LLMBaseException):
    """Raised when LLM text generation fails during inference."""

    def __init__(self, request_id: str, reason: str) -> None:
        super().__init__(
            message=f"LLM inference generation failed for request '{request_id}': {reason}",
            details={"request_id": request_id, "reason": reason},
        )


class ModelTimeoutError(LLMBaseException):
    """Raised when LLM generation exceeds allowed execution timeout."""

    def __init__(self, request_id: str, timeout_seconds: float) -> None:
        super().__init__(
            message=f"LLM inference generation timed out after {timeout_seconds}s for request '{request_id}'.",
            details={"request_id": request_id, "timeout_seconds": timeout_seconds},
        )


class ProviderUnavailableError(LLMBaseException):
    """Raised when requested LLM provider bindings or service are unavailable."""

    def __init__(self, provider_name: str, reason: str) -> None:
        super().__init__(
            message=f"LLM Provider '{provider_name}' is unavailable: {reason}",
            details={"provider_name": provider_name, "reason": reason},
        )


class OrchestratorError(LLMBaseException):
    """Base exception class for AI Orchestrator errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)


class ToolSelectionError(OrchestratorError):
    """Raised when selected tool is invalid or not registered in ToolRegistry."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            message=f"Selected tool '{tool_name}' is not registered or unavailable.",
            details={"tool_name": tool_name},
        )


class MaxStepsExceededError(OrchestratorError):
    """Raised when reasoning loop exceeds maximum allowed step count."""

    def __init__(self, request_id: str, max_steps: int) -> None:
        super().__init__(
            message=f"Orchestration request '{request_id}' exceeded maximum step limit ({max_steps}).",
            details={"request_id": request_id, "max_steps": max_steps},
        )


class PlanExecutionError(OrchestratorError):
    """Raised when tool execution step within plan fails fatally."""

    def __init__(self, step_number: int, tool_name: str, reason: str) -> None:
        super().__init__(
            message=f"Action plan step {step_number} ('{tool_name}') failed: {reason}",
            details={
                "step_number": step_number,
                "tool_name": tool_name,
                "reason": reason,
            },
        )
