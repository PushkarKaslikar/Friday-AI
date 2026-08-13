"""Central Model Manager & Gateway for Local LLM Runtime.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import threading
import time
from collections.abc import Iterator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.errors.exceptions import (
    ModelInferenceError,
    ModelLoadError,
    ModelNotReadyError,
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
from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    AIResponse,
    ModelCapabilities,
    ModelLifecycleState,
    ModelMetadata,
)
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.ai.providers.llama_cpp_provider import LlamaCppProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.provider_interface import IAIModelProvider
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus

T = TypeVar("T", bound=BaseModel)


class LLMModelManager(BaseService):
    """Central service managing local LLM lifecycle, provider delegation, and thread-safe inference."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        provider: IAIModelProvider | None = None,
    ) -> None:
        super().__init__(name="LLMModelManager", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self._lock = threading.Lock()

        self._model_config: AIModelConfiguration = self._load_model_configuration()
        self._provider: IAIModelProvider = provider or self._select_provider(
            self._model_config.provider
        )
        self._last_error: str | None = None

    @property
    def model_config(self) -> AIModelConfiguration:
        """Active model configuration settings."""
        return self._model_config

    @property
    def provider(self) -> IAIModelProvider:
        """Active model provider instance."""
        return self._provider

    @property
    def lifecycle_state(self) -> ModelLifecycleState:
        """Current model lifecycle state."""
        return self._provider.state

    def set_provider(self, provider: IAIModelProvider) -> None:
        """Explicitly switch active provider instance."""
        with self._lock:
            if self._provider.state != ModelLifecycleState.UNINITIALIZED:
                self._provider.unload_model()
            self._provider = provider
            self._provider.initialize(self._model_config)
            logger.info(
                f"LLMModelManager: Switched active provider to '{provider.provider_name}'."
            )

    def _select_provider(self, provider_type: str) -> IAIModelProvider:
        """Instantiate provider by type string."""
        clean = provider_type.lower()
        if clean == "ollama":
            p = OllamaProvider()
        elif clean == "fake":
            p = FakeAIModelProvider()
        else:
            p = LlamaCppProvider()

        p.initialize(self._model_config)
        return p

    def _load_model_configuration(self) -> AIModelConfiguration:
        """Load LLM settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "llm"):
                cfg = settings.llm
                return AIModelConfiguration(
                    provider=cfg.provider,
                    model_name=cfg.model_name,
                    model_path=cfg.model_path,
                    preload_model=cfg.preload_model,
                    context_size=cfg.context_size,
                    temperature=cfg.temperature,
                    top_p=cfg.top_p,
                    top_k=cfg.top_k,
                    max_tokens=cfg.max_tokens,
                    use_cuda=cfg.use_cuda,
                    gpu_layers=cfg.gpu_layers,
                    threads=cfg.threads,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"LLMModelManager: Failed to load settings, using defaults: {exc}"
            )

        return AIModelConfiguration()

    def _do_initialize(self) -> None:
        """Initialize provider with configuration."""
        self._provider.initialize(self._model_config)
        logger.info("LLMModelManager: Service initialized.")

    def _do_start(self) -> None:
        """Start service. If preload_model=True, load model on startup."""
        if self._model_config.preload_model:
            logger.info(
                "LLMModelManager: Preload model enabled. Preloading local LLM on startup..."
            )
            try:
                self.load_model()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"LLMModelManager: Failed to preload LLM model on startup: {exc}"
                )
        else:
            logger.info(
                "LLMModelManager: Started in lazy-load mode (model will load on first inference)."
            )

    def _do_stop(self) -> None:
        """Stop service and unload model from memory."""
        self.unload_model()
        logger.info("LLMModelManager: Service stopped and model resources freed.")

    def load_model(self, model_path: str | None = None) -> None:
        """Load configured local LLM model."""
        with self._lock:
            path = model_path or self._model_config.model_path
            self.event_bus.publish(
                ModelLoadingStarted(
                    provider_name=self._provider.provider_name, model_path=path
                )
            )
            t_start = time.time()

            try:
                self._provider.load_model(path)
                load_ms = (time.time() - t_start) * 1000.0
                meta = self._provider.get_metadata()
                self._last_error = None

                self.event_bus.publish(
                    ModelLoaded(
                        provider_name=self._provider.provider_name,
                        model_path=path,
                        device=meta.device,
                        load_duration_ms=load_ms,
                    )
                )
                logger.info(
                    f"LLMModelManager: Loaded model '{meta.model_name}' on device '{meta.device}'."
                )
            except Exception as exc:
                self._last_error = str(exc)
                self.event_bus.publish(
                    ModelLoadFailed(
                        provider_name=self._provider.provider_name,
                        model_path=path,
                        error_message=str(exc),
                    )
                )
                raise ModelLoadError(model_path=path, reason=str(exc)) from exc

    def unload_model(self) -> None:
        """Unload local model."""
        with self._lock:
            if self._provider.state != ModelLifecycleState.UNINITIALIZED:
                self._provider.unload_model()
                self.event_bus.publish(
                    ModelUnloaded(provider_name=self._provider.provider_name)
                )

    def generate(self, request: AIRequest) -> AIResponse:
        """Execute text generation request. Auto-loads model if uninitialized."""
        t_start = time.time()
        with self._lock:
            if self._provider.state == ModelLifecycleState.UNINITIALIZED:
                logger.info(
                    "LLMModelManager: Model is UNINITIALIZED. Auto-loading model for request..."
                )
                self.load_model()

            if self._provider.state != ModelLifecycleState.READY:
                raise ModelNotReadyError(state=self._provider.state.value)

            self.event_bus.publish(
                GenerationStarted(
                    request_id=request.request_id, prompt_length=len(request.prompt)
                )
            )

        try:
            response = self._provider.generate(request)
            duration_ms = (time.time() - t_start) * 1000.0

            self.event_bus.publish(
                GenerationCompleted(
                    request_id=request.request_id,
                    text_length=len(response.text),
                    tokens_per_second=response.tokens_per_second,
                    duration_ms=duration_ms,
                )
            )
            return response
        except Exception as exc:
            self.event_bus.publish(
                GenerationFailed(request_id=request.request_id, error_message=str(exc))
            )
            raise ModelInferenceError(
                request_id=request.request_id, reason=str(exc)
            ) from exc

    def generate_stream(self, request: AIRequest) -> Iterator[str]:
        """Stream response tokens from active provider."""
        if self._provider.state == ModelLifecycleState.UNINITIALIZED:
            self.load_model()

        return self._provider.generate_stream(request)

    def generate_structured(self, request: AIRequest, schema_cls: type[T]) -> T:
        """Generate structured response validated against Pydantic schema."""
        if self._provider.state == ModelLifecycleState.UNINITIALIZED:
            self.load_model()

        return self._provider.generate_structured(request, schema_cls)

    def get_capabilities(self) -> ModelCapabilities:
        """Return active model capabilities."""
        return self._provider.get_capabilities()

    def get_metadata(self) -> ModelMetadata:
        """Return active model metadata."""
        return self._provider.get_metadata()

    def get_health_report(self) -> dict[str, Any]:
        """Generate comprehensive diagnostic health report."""
        meta = self.get_metadata()
        caps = self.get_capabilities()

        status = "HEALTHY"
        if self._provider.state == ModelLifecycleState.ERROR or self._last_error:
            status = "DEGRADED"
        elif self._provider.state == ModelLifecycleState.UNINITIALIZED:
            status = "UNINITIALIZED"

        return {
            "status": status,
            "provider": meta.provider_name,
            "model_name": meta.model_name,
            "model_path": meta.model_path,
            "state": self._provider.state.value,
            "device": meta.device,
            "format": meta.format,
            "context_size": meta.context_window,
            "model_loaded": self._provider.state
            in (ModelLifecycleState.READY, ModelLifecycleState.GENERATING),
            "supports_cuda": caps.supports_cuda,
            "supports_streaming": caps.supports_streaming,
            "supports_structured_output": caps.supports_structured_output,
            "last_error": self._last_error,
        }

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
