"""Domain models and data structures for Local LLM Runtime & Model Provider Foundation.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class MessageRole(str, Enum):
    """Role classification for chat messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Structured message in a conversation sequence."""

    role: MessageRole
    content: str
    name: str | None = None


class ModelLifecycleState(str, Enum):
    """Model runtime lifecycle state machine states."""

    UNINITIALIZED = "UNINITIALIZED"
    LOADING = "LOADING"
    READY = "READY"
    GENERATING = "GENERATING"
    UNLOADING = "UNLOADING"
    ERROR = "ERROR"


@dataclass
class ModelCapabilities:
    """Capabilities supported by the active model provider."""

    supports_streaming: bool = True
    supports_structured_output: bool = True
    supports_chat: bool = True
    supports_tool_calling: bool = True
    supports_cuda: bool = False
    context_window_size: int = 4096


@dataclass
class ModelMetadata:
    """Metadata describing a loaded LLM model."""

    provider_name: str = "llama_cpp"
    model_name: str = "Unknown"
    model_path: str = ""
    format: str = "GGUF"
    device: str = "CPU"
    parameters_count: str = "Unknown"
    quantization: str = "Unknown"
    context_window: int = 4096


@dataclass
class AIRequest:
    """Structured inference request contract."""

    request_id: str
    prompt: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    system_instruction: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 512
    seed: int | None = None
    stop_sequences: list[str] = field(default_factory=list)
    response_format: Literal["text", "json"] = "text"
    stream: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class AIResponse:
    """Structured inference response contract."""

    request_id: str
    text: str = ""
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    generation_duration_ms: float = 0.0
    model_info: ModelMetadata | None = None
    error: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AIModelConfiguration:
    """Common model configuration settings."""

    provider: str = "llama_cpp"
    model_name: str = "tinyllama-1.1b-chat.Q4_K_M.gguf"
    model_path: str = "models/llm/tinyllama-1.1b-chat.Q4_K_M.gguf"
    preload_model: bool = False
    context_size: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 512
    use_cuda: bool = False
    gpu_layers: int = 0
    threads: int = 4
