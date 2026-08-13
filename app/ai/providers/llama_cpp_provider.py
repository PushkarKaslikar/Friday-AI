"""llama.cpp GGUF local model provider implementation.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import json
import os
import threading
import time
from collections.abc import Iterator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.errors.exceptions import (
    ModelInferenceError,
    ModelNotFoundError,
    ModelNotReadyError,
    ProviderUnavailableError,
)
from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    AIResponse,
    MessageRole,
    ModelCapabilities,
    ModelLifecycleState,
    ModelMetadata,
)
from app.ai.providers.provider_interface import IAIModelProvider
from app.logging import logger

T = TypeVar("T", bound=BaseModel)


class LlamaCppProvider(IAIModelProvider):
    """Primary local GGUF provider using llama-cpp-python binding."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = ModelLifecycleState.UNINITIALIZED
        self._config: AIModelConfiguration = AIModelConfiguration()
        self._model_instance: Any = None
        self._llama_module: Any = None
        self._load_duration_ms: float = 0.0

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "llama_cpp"

    @property
    def state(self) -> ModelLifecycleState:
        """Return current provider lifecycle state."""
        with self._lock:
            return self._state

    def initialize(self, config: AIModelConfiguration) -> None:
        """Initialize provider with configuration settings."""
        with self._lock:
            self._config = config
            logger.info(
                f"LlamaCppProvider: Initialized with config model_path='{config.model_path}'."
            )

    def load_model(self, model_path: str | None = None) -> None:
        """Load local GGUF model into memory using llama-cpp-python binding."""
        with self._lock:
            if self._state in (
                ModelLifecycleState.READY,
                ModelLifecycleState.GENERATING,
            ):
                logger.info("LlamaCppProvider: Model is already loaded and READY.")
                return

            self._state = ModelLifecycleState.LOADING
            path = model_path or self._config.model_path

            # 1. Verify file existence
            if not path or not os.path.exists(path):
                self._state = ModelLifecycleState.ERROR
                raise ModelNotFoundError(model_path=path or "Unconfigured")

            # 2. Check bindings availability
            try:
                import llama_cpp  # type: ignore # noqa: PGO002

                self._llama_module = llama_cpp
            except ImportError:
                self._state = ModelLifecycleState.ERROR
                raise ProviderUnavailableError(
                    provider_name=self.provider_name,
                    reason="llama-cpp-python package is not installed in current Python environment.",
                )

            # 3. Instantiate model
            t_start = time.time()
            try:
                gpu_layers = self._config.gpu_layers if self._config.use_cuda else 0
                self._model_instance = self._llama_module.Llama(
                    model_path=path,
                    n_ctx=self._config.context_size,
                    n_gpu_layers=gpu_layers,
                    n_threads=self._config.threads,
                    verbose=False,
                )
                self._load_duration_ms = (time.time() - t_start) * 1000.0
                self._state = ModelLifecycleState.READY
                logger.info(
                    f"LlamaCppProvider: Successfully loaded model '{path}' in {self._load_duration_ms:.2f}ms."
                )
            except Exception as exc:
                self._state = ModelLifecycleState.ERROR
                logger.error(f"LlamaCppProvider: Failed to load model '{path}': {exc}")
                raise ModelInferenceError(request_id="LOAD", reason=str(exc)) from exc

    def unload_model(self) -> None:
        """Unload model instance and free memory."""
        with self._lock:
            if self._state == ModelLifecycleState.UNINITIALIZED:
                return
            self._state = ModelLifecycleState.UNLOADING
            if self._model_instance is not None:
                del self._model_instance
                self._model_instance = None
            self._state = ModelLifecycleState.UNINITIALIZED
            logger.info("LlamaCppProvider: Unloaded model successfully.")

    def generate(self, request: AIRequest) -> AIResponse:
        """Execute text generation request using loaded GGUF model."""
        with self._lock:
            if self._state != ModelLifecycleState.READY or self._model_instance is None:
                raise ModelNotReadyError(state=self._state.value)

            self._state = ModelLifecycleState.GENERATING

        t_start = time.time()
        try:
            formatted_prompt = self._format_prompt(request)
            raw_response = self._model_instance(
                prompt=formatted_prompt,
                max_tokens=request.max_tokens or self._config.max_tokens,
                temperature=request.temperature or self._config.temperature,
                top_p=request.top_p or self._config.top_p,
                top_k=request.top_k or self._config.top_k,
                stop=request.stop_sequences or None,
            )

            duration_ms = (time.time() - t_start) * 1000.0
            generated_text = raw_response["choices"][0]["text"].strip()
            usage = raw_response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            tps = (
                (completion_tokens / (duration_ms / 1000.0)) if duration_ms > 0 else 0.0
            )

            with self._lock:
                self._state = ModelLifecycleState.READY

            return AIResponse(
                request_id=request.request_id,
                text=generated_text,
                finish_reason=raw_response["choices"][0].get("finish_reason", "stop"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                tokens_per_second=round(tps, 2),
                generation_duration_ms=round(duration_ms, 2),
                model_info=self.get_metadata(),
            )
        except Exception as exc:
            with self._lock:
                self._state = ModelLifecycleState.READY
            logger.error(
                f"LlamaCppProvider: Generation failed for request '{request.request_id}': {exc}"
            )
            raise ModelInferenceError(
                request_id=request.request_id, reason=str(exc)
            ) from exc

    def generate_stream(self, request: AIRequest) -> Iterator[str]:
        """Stream generated text tokens iteratively."""
        if self._state != ModelLifecycleState.READY or self._model_instance is None:
            raise ModelNotReadyError(state=self._state.value)

        formatted_prompt = self._format_prompt(request)
        stream_resp = self._model_instance(
            prompt=formatted_prompt,
            max_tokens=request.max_tokens or self._config.max_tokens,
            temperature=request.temperature or self._config.temperature,
            top_p=request.top_p or self._config.top_p,
            top_k=request.top_k or self._config.top_k,
            stop=request.stop_sequences or None,
            stream=True,
        )

        for chunk in stream_resp:
            delta = chunk["choices"][0].get("text", "")
            if delta:
                yield delta

    def generate_structured(self, request: AIRequest, schema_cls: type[T]) -> T:
        """Generate structured response and parse into Pydantic schema."""
        request.response_format = "json"
        system_json_prompt = f"Respond ONLY in valid JSON matching this schema: {schema_cls.model_json_schema()}"
        if request.system_instruction:
            request.system_instruction = (
                f"{request.system_instruction}\n{system_json_prompt}"
            )
        else:
            request.system_instruction = system_json_prompt

        response = self.generate(request)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif clean_text.startswith("```"):
            clean_text = clean_text.split("```", 1)[-1].split("```", 1)[0].strip()

        data = json.loads(clean_text)
        return schema_cls.model_validate(data)

    def get_capabilities(self) -> ModelCapabilities:
        """Return capabilities supported by llama.cpp provider."""
        return ModelCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_chat=True,
            supports_cuda=self._config.use_cuda,
            context_window_size=self._config.context_size,
        )

    def get_metadata(self) -> ModelMetadata:
        """Return metadata describing active model."""
        return ModelMetadata(
            provider_name=self.provider_name,
            model_name=self._config.model_name,
            model_path=self._config.model_path,
            format="GGUF",
            device="CUDA" if self._config.use_cuda else "CPU",
            context_window=self._config.context_size,
        )

    def _format_prompt(self, request: AIRequest) -> str:
        """Format request messages/system instruction into standard prompt text."""
        prompt_parts = []
        if request.system_instruction:
            prompt_parts.append(f"<|system|>\n{request.system_instruction}")

        if request.messages:
            for msg in request.messages:
                role_str = (
                    msg.role.value
                    if isinstance(msg.role, MessageRole)
                    else str(msg.role)
                )
                prompt_parts.append(f"<|{role_str}|>\n{msg.content}")
            prompt_parts.append("<|assistant|>\n")
        elif request.prompt:
            prompt_parts.append(request.prompt)

        return "\n".join(prompt_parts)
