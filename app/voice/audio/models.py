"""Domain models and data structures for Phase 3.1 Audio Engine Foundation."""

from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from app.utilities.system_utils import get_timestamp_str


class AudioEngineState(str, Enum):
    """Lifecycle states of the Audio Engine."""

    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class AudioStreamState(str, Enum):
    """Lifecycle states of individual input/output streams."""

    NOT_INITIALIZED = "NOT_INITIALIZED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class AudioDevice(BaseModel):
    """Strongly typed representation of an enumerated audio device."""

    device_id: int | str = Field(
        description="Unique device index or stable hardware identifier"
    )
    name: str = Field(description="Device display name reported by OS")
    host_api: str = Field(
        default="MME/WASAPI/DirectSound", description="Host API interface name"
    )
    is_input: bool = Field(
        default=False, description="True if device supports audio capture"
    )
    is_output: bool = Field(
        default=False, description="True if device supports audio playback"
    )
    max_input_channels: int = Field(
        default=0, description="Maximum supported input channels"
    )
    max_output_channels: int = Field(
        default=0, description="Maximum supported output channels"
    )
    default_sample_rate: int = Field(
        default=44100, description="Default device sample rate in Hz"
    )
    supported_sample_rates: list[int] = Field(
        default_factory=lambda: [16000, 44100, 48000],
        description="List of verified supported sample rates in Hz",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional device properties"
    )


class AudioConfiguration(BaseModel):
    """Configuration parameters container for input and output streams."""

    sample_rate: int = Field(
        default=16000, description="Sample rate in Hz (16kHz preferred)"
    )
    input_channels: int = Field(
        default=1, description="Number of input channels (1 = mono)"
    )
    output_channels: int = Field(
        default=2, description="Number of output channels (2 = stereo)"
    )
    block_size: int = Field(default=512, description="Frames per callback block")
    dtype: str = Field(
        default="float32", description="Data type representation ('float32')"
    )
    latency_mode: str = Field(
        default="low", description="Latency target mode ('low', 'high', 'balanced')"
    )
    input_device_id: int | str | None = Field(
        default=None, description="Explicit input device selection"
    )
    output_device_id: int | str | None = Field(
        default=None, description="Explicit output device selection"
    )
    buffer_size_seconds: float = Field(
        default=5.0, description="Maximum ring buffer depth in seconds"
    )
    auto_fallback: bool = Field(
        default=True, description="Fallback to default device on disconnect"
    )


class AudioFrame(BaseModel):
    """Standardized real-time audio frame abstraction passed to consumers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    samples: np.ndarray = Field(description="Numpy array containing audio PCM samples")
    timestamp: float = Field(description="Monotonic high-precision capture timestamp")
    sample_rate: int = Field(default=16000, description="Frame sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    frame_count: int = Field(description="Total number of audio samples in array")
    duration: float = Field(description="Frame duration in seconds")
    timestamp_str: str = Field(
        default_factory=get_timestamp_str, description="ISO timestamp string"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional frame metadata"
    )

    @classmethod
    def create(
        cls,
        samples: np.ndarray,
        timestamp: float,
        sample_rate: int = 16000,
        channels: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> "AudioFrame":
        """Factory method computing duration and frame_count from raw numpy samples."""
        frame_count = samples.shape[0] if len(samples.shape) > 0 else len(samples)
        duration = round(frame_count / max(1, sample_rate), 6)
        return cls(
            samples=samples,
            timestamp=timestamp,
            sample_rate=sample_rate,
            channels=channels,
            frame_count=frame_count,
            duration=duration,
            metadata=metadata or {},
        )
