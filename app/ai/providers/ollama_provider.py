"""Ollama REST API provider boundary for local models.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import json
import threading
import time
import urllib.request
from collections.abc import Iterator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.errors.exceptions import ModelInferenceError, ProviderUnavailableError
from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    AIResponse,
    ModelCapabilities,
    ModelLifecycleState,
    ModelMetadata,
)
from app.ai.providers.provider_interface import IAIModelProvider
from app.logging import logger

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(IAIModelProvider):
    """Provider boundary for communicating with local Ollama HTTP REST service."""

    def __init__(self, host: str = "http://localhost:11434") -> None:
        self.host = host.rstrip("/")
        self._lock = threading.Lock()
        self._state = ModelLifecycleState.UNINITIALIZED
        self._config: AIModelConfiguration = AIModelConfiguration()

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "ollama"

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
                f"OllamaProvider: Initialized with host '{self.host}' and model '{config.model_name}'."
            )

    def load_model(self, model_path: str | None = None) -> None:
        """Verify Ollama host service availability and set READY state."""
        with self._lock:
            self._state = ModelLifecycleState.LOADING
            try:
                req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        self._state = ModelLifecycleState.READY
                        logger.info(
                            "OllamaProvider: Connected to local Ollama service successfully."
                        )
                    else:
                        self._state = ModelLifecycleState.ERROR
                        raise ProviderUnavailableError(
                            provider_name=self.provider_name,
                            reason=f"Ollama returned HTTP status {resp.status}",
                        )
            except Exception as exc:
                self._state = ModelLifecycleState.ERROR
                raise ProviderUnavailableError(
                    provider_name=self.provider_name,
                    reason=f"Could not connect to Ollama service at {self.host}: {exc}",
                ) from exc

    def unload_model(self) -> None:
        """Reset provider state."""
        with self._lock:
            self._state = ModelLifecycleState.UNINITIALIZED
            logger.info("OllamaProvider: Model connection closed.")

    def generate(self, request: AIRequest) -> AIResponse:
        """Send inference request to local Ollama /api/generate REST endpoint."""
        t_start = time.time()
        payload = {
            "model": self._config.model_name or "tinyllama",
            "prompt": request.prompt or self._format_messages(request),
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k,
                "num_predict": request.max_tokens,
            },
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            http_req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(http_req, timeout=30.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            duration_ms = (time.time() - t_start) * 1000.0
            generated_text = result.get("response", "").strip()
            eval_count = result.get("eval_count", 0)
            tps = (eval_count / (duration_ms / 1000.0)) if duration_ms > 0 else 0.0

            return AIResponse(
                request_id=request.request_id,
                text=generated_text,
                finish_reason="stop",
                prompt_tokens=result.get("prompt_eval_count", 0),
                completion_tokens=eval_count,
                total_tokens=result.get("prompt_eval_count", 0) + eval_count,
                tokens_per_second=round(tps, 2),
                generation_duration_ms=round(duration_ms, 2),
                model_info=self.get_metadata(),
            )
        except Exception as exc:
            logger.error(
                f"OllamaProvider: Generation failed for request '{request.request_id}': {exc}"
            )
            raise ModelInferenceError(
                request_id=request.request_id, reason=str(exc)
            ) from exc

    def generate_stream(self, request: AIRequest) -> Iterator[str]:
        """Stream response chunks from Ollama API."""
        payload = {
            "model": self._config.model_name or "tinyllama",
            "prompt": request.prompt or self._format_messages(request),
            "stream": True,
        }
        req_data = json.dumps(payload).encode("utf-8")
        http_req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(http_req, timeout=30.0) as resp:
            for line in resp:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    delta = chunk.get("response", "")
                    if delta:
                        yield delta

    def generate_structured(self, request: AIRequest, schema_cls: type[T]) -> T:
        """Generate structured response validated against Pydantic schema."""
        request.prompt = f"{request.prompt}\nRespond ONLY in valid JSON matching schema: {schema_cls.model_json_schema()}"
        resp = self.generate(request)
        clean = resp.text.strip()
        if clean.startswith("```json"):
            clean = clean.split("```json", 1)[-1].split("```", 1)[0].strip()
        data = json.loads(clean)
        return schema_cls.model_validate(data)

    def get_capabilities(self) -> ModelCapabilities:
        """Return capabilities of Ollama provider."""
        return ModelCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_chat=True,
            supports_cuda=False,
            context_window_size=self._config.context_size,
        )

    def get_metadata(self) -> ModelMetadata:
        """Return metadata describing Ollama model."""
        return ModelMetadata(
            provider_name=self.provider_name,
            model_name=self._config.model_name,
            model_path=f"ollama://{self._config.model_name}",
            format="Ollama",
            device="Ollama-Service",
            context_window=self._config.context_size,
        )

    def _format_messages(self, request: AIRequest) -> str:
        """Format ChatMessages to prompt string."""
        parts = []
        if request.system_instruction:
            parts.append(f"System: {request.system_instruction}")
        for m in request.messages:
            parts.append(f"{m.role.value.capitalize()}: {m.content}")
        return "\n".join(parts)
