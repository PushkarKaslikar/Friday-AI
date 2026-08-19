"""Deterministic mock provider for fast offline unit testing.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import threading
import time
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
from app.ai.providers.provider_interface import IAIModelProvider

T = TypeVar("T", bound=BaseModel)


class FakeAIModelProvider(IAIModelProvider):
    """Mock/test double provider simulating local LLM generation."""

    def __init__(
        self,
        default_response_text: str = "FRIDAY LOCAL LLM TEST PASSED",
        should_fail: bool = False,
    ) -> None:
        self.default_response_text = default_response_text
        self.should_fail = should_fail
        self._lock = threading.Lock()
        self._state = ModelLifecycleState.UNINITIALIZED
        self._config = AIModelConfiguration()

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "fake"

    @property
    def state(self) -> ModelLifecycleState:
        """Return current provider state."""
        with self._lock:
            return self._state

    def initialize(self, config: AIModelConfiguration) -> None:
        """Initialize fake provider."""
        with self._lock:
            self._config = config

    def load_model(self, model_path: str | None = None) -> None:
        """Simulate model load."""
        with self._lock:
            self._state = ModelLifecycleState.LOADING
            if self.should_fail:
                self._state = ModelLifecycleState.ERROR
                raise RuntimeError("FakeProvider load failed intentionally.")
            self._state = ModelLifecycleState.READY

    def unload_model(self) -> None:
        """Simulate model unload."""
        with self._lock:
            self._state = ModelLifecycleState.UNINITIALIZED

    def generate(self, request: AIRequest) -> AIResponse:
        """Simulate response text generation."""
        with self._lock:
            if self.should_fail:
                raise RuntimeError("FakeProvider generation failed intentionally.")

            self._state = ModelLifecycleState.GENERATING

        time.sleep(0.01)

        text = self.default_response_text
        if self.default_response_text == "FRIDAY LOCAL LLM TEST PASSED" and request.prompt:
            p_lower = request.prompt.lower()
            if "hello" in p_lower or "hi" in p_lower or "hey" in p_lower:
                text = "Hello! I am Friday, your personal desktop AI assistant. How can I assist you today?"
            elif "who are you" in p_lower or "what are you" in p_lower:
                text = "I am Friday, an agentic desktop AI assistant with local tool calling and system control."
            elif "time" in p_lower:
                text = f"The current system time is {time.strftime('%I:%M %p')}."
            elif "date" in p_lower:
                text = f"Today is {time.strftime('%A, %B %d, %Y')}."
            else:
                text = "I am ready to help you with desktop automation, opening applications, and system management."

        with self._lock:
            self._state = ModelLifecycleState.READY

        return AIResponse(
            request_id=request.request_id,
            text=text,
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=15,
            total_tokens=25,
            tokens_per_second=150.0,
            generation_duration_ms=10.0,
            model_info=self.get_metadata(),
        )



    def generate_stream(self, request: AIRequest) -> Iterator[str]:
        """Simulate token streaming."""
        tokens = ["FRIDAY ", "LOCAL ", "LLM ", "TEST ", "PASSED"]
        for t in tokens:
            time.sleep(0.005)
            yield t

    def generate_structured(self, request: AIRequest, schema_cls: type[T]) -> T:
        """Simulate structured schema generation."""
        dummy_data = {}
        for fname, field in schema_cls.model_fields.items():
            if field.annotation is int:
                dummy_data[fname] = 42
            elif field.annotation is bool:
                dummy_data[fname] = True
            else:
                dummy_data[fname] = f"test_{fname}"
        return schema_cls.model_validate(dummy_data)

    def get_capabilities(self) -> ModelCapabilities:
        """Return capabilities."""
        return ModelCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_chat=True,
            supports_cuda=False,
            context_window_size=4096,
        )

    def get_metadata(self) -> ModelMetadata:
        """Return metadata."""
        return ModelMetadata(
            provider_name=self.provider_name,
            model_name="FakeModel-v1",
            model_path="fake://model",
            format="MOCK",
            device="CPU",
            context_window=4096,
        )
