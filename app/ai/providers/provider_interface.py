"""Abstract boundary contract for Local LLM Model Providers.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    AIResponse,
    ModelCapabilities,
    ModelLifecycleState,
    ModelMetadata,
)

T = TypeVar("T", bound=BaseModel)


class IAIModelProvider(ABC):
    """Abstract provider interface defining standard operations for local LLM runtimes."""

    @abstractmethod
    def initialize(self, config: AIModelConfiguration) -> None:
        """Initialize provider with configuration."""

    @abstractmethod
    def load_model(self, model_path: str | None = None) -> None:
        """Load GGUF or local model file into memory."""

    @abstractmethod
    def unload_model(self) -> None:
        """Unload model and free allocated memory/VRAM."""

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Execute text generation request."""

    @abstractmethod
    def generate_stream(self, request: AIRequest) -> Iterator[str]:
        """Stream generated response text tokens iteratively."""

    @abstractmethod
    def generate_structured(self, request: AIRequest, schema_cls: type[T]) -> T:
        """Generate response and validate output against Pydantic schema."""

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Return capabilities supported by this provider."""

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Return model metadata describing active loaded model."""

    @property
    @abstractmethod
    def state(self) -> ModelLifecycleState:
        """Return current provider lifecycle state."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier name."""
