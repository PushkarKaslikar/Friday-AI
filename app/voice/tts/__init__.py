"""Text-to-Speech (TTS) Subsystem for Friday AI Assistant.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

from app.voice.tts.audio_adapter import TTSAudioAdapter
from app.voice.tts.diagnostics import TTSDiagnostics
from app.voice.tts.events import (
    TTSError,
    TTSFailed,
    TTSModelLoaded,
    TTSModelUnloaded,
    TTSPlaybackCompleted,
    TTSPlaybackStarted,
    TTSStateChanged,
    TTSStopped,
    TTSSynthesisCompleted,
    TTSSynthesisStarted,
)
from app.voice.tts.metrics import TTSMetrics
from app.voice.tts.models import (
    TTSConfiguration,
    TTSResult,
    TTSState,
)
from app.voice.tts.piper_tts_provider import PiperTTSProvider
from app.voice.tts.tts_provider_interface import ITTSProvider
from app.voice.tts.tts_service import TTSService
from app.voice.tts.tts_service_interface import ITTSService

__all__ = [
    "ITTSProvider",
    "ITTSService",
    "PiperTTSProvider",
    "TTSAudioAdapter",
    "TTSConfiguration",
    "TTSDiagnostics",
    "TTSError",
    "TTSFailed",
    "TTSMetrics",
    "TTSModelLoaded",
    "TTSModelUnloaded",
    "TTSPlaybackCompleted",
    "TTSPlaybackStarted",
    "TTSResult",
    "TTSService",
    "TTSState",
    "TTSStateChanged",
    "TTSStopped",
    "TTSSynthesisCompleted",
    "TTSSynthesisStarted",
]
