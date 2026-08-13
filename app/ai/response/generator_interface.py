"""Abstract boundary contract for Dynamic Response Generation Engine.

Phase 4.5 - Dynamic Response Generation Engine
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.ai.response.models import ResponseGenerationRequest, ResponseResult


class IResponseGenerator(ABC):
    """Abstract interface contract for Dynamic Response Generation Engine."""

    @abstractmethod
    def generate_response(self, request: ResponseGenerationRequest) -> ResponseResult:
        """Execute full response generation turn with validation and fallback."""

    @abstractmethod
    def stream_response(self, request: ResponseGenerationRequest) -> Iterator[str]:
        """Stream generated response text tokens iteratively."""

    @abstractmethod
    def format_fallback_response(
        self, request: ResponseGenerationRequest, error_reason: str
    ) -> ResponseResult:
        """Generate deterministic factual fallback response when LLM fails or times out."""
