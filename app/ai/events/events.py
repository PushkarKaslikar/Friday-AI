"""EventBus typed events for Local LLM Runtime.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import time
from dataclasses import dataclass, field

from app.services.events.event_models import Event


@dataclass
class ModelLoadingStarted(Event):
    """Event published when model loading begins."""

    provider_name: str = ""
    model_path: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ModelLoadingStarted", init=False)


@dataclass
class ModelLoaded(Event):
    """Event published when local model finishes loading."""

    provider_name: str = ""
    model_path: str = ""
    device: str = "CPU"
    load_duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ModelLoaded", init=False)


@dataclass
class ModelUnloaded(Event):
    """Event published when local model is unloaded from memory."""

    provider_name: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ModelUnloaded", init=False)


@dataclass
class ModelLoadFailed(Event):
    """Event published when local model load fails."""

    provider_name: str = ""
    model_path: str = ""
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="ModelLoadFailed", init=False)


@dataclass
class GenerationStarted(Event):
    """Event published when LLM generation request starts."""

    request_id: str = ""
    prompt_length: int = 0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GenerationStarted", init=False)


@dataclass
class GenerationCompleted(Event):
    """Event published when LLM text generation finishes."""

    request_id: str = ""
    text_length: int = 0
    tokens_per_second: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GenerationCompleted", init=False)


@dataclass
class GenerationFailed(Event):
    """Event published when LLM generation encounters an error."""

    request_id: str = ""
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="GenerationFailed", init=False)
