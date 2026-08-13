"""Local LLM Runtime & Model Provider Foundation for Friday AI Assistant.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

from app.ai.diagnostics.diagnostics import LLMDiagnostics
from app.ai.errors.exceptions import (
    LLMBaseException,
    ModelInferenceError,
    ModelLoadError,
    ModelNotConfiguredError,
    ModelNotFoundError,
    ModelNotReadyError,
    ModelTimeoutError,
    ProviderUnavailableError,
)
from app.ai.events.events import (
    GenerationCompleted,
    GenerationFailed,
    GenerationStarted,
    ModelLoaded,
    ModelLoadFailed,
    ModelLoadingStarted,
    ModelUnloaded,
)
from app.ai.gateway.model_manager import LLMModelManager
from app.ai.metrics.metrics import LLMMetrics
from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    AIResponse,
    ChatMessage,
    MessageRole,
    ModelCapabilities,
    ModelLifecycleState,
    ModelMetadata,
)
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.ai.providers.llama_cpp_provider import LlamaCppProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.provider_interface import IAIModelProvider

__all__ = [
    "AIModelConfiguration",
    "AIRequest",
    "AIResponse",
    "ChatMessage",
    "FakeAIModelProvider",
    "GenerationCompleted",
    "GenerationFailed",
    "GenerationStarted",
    "IAIModelProvider",
    "LLMBaseException",
    "LLMDiagnostics",
    "LLMMetrics",
    "LLMModelManager",
    "LlamaCppProvider",
    "MessageRole",
    "ModelCapabilities",
    "ModelInferenceError",
    "ModelLifecycleState",
    "ModelLoadError",
    "ModelLoadFailed",
    "ModelLoaded",
    "ModelLoadingStarted",
    "ModelMetadata",
    "ModelNotConfiguredError",
    "ModelNotFoundError",
    "ModelNotReadyError",
    "ModelTimeoutError",
    "ModelUnloaded",
    "OllamaProvider",
    "ProviderUnavailableError",
]
