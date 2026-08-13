"""Speech-to-Text (STT) Subsystem Package Exports.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

from app.voice.stt.diagnostics import STTDiagnostics
from app.voice.stt.events import (
    STTError,
    STTModelLoaded,
    STTModelUnloaded,
    STTStateChanged,
    TranscriptionCancelled,
    TranscriptionCompleted,
    TranscriptionFailed,
    TranscriptionStarted,
)
from app.voice.stt.faster_whisper_engine import FasterWhisperSTTEngine
from app.voice.stt.metrics import STTMetrics
from app.voice.stt.models import (
    STTConfiguration,
    STTState,
    TranscriptionResult,
    TranscriptSegment,
)
from app.voice.stt.speech_buffer import SpeechSegmentBuffer
from app.voice.stt.stt_engine_interface import ISTTEngine
from app.voice.stt.stt_service import STTService
from app.voice.stt.stt_service_interface import ISTTService

__all__ = [
    "FasterWhisperSTTEngine",
    "ISTTEngine",
    "ISTTService",
    "STTConfiguration",
    "STTDiagnostics",
    "STTError",
    "STTMetrics",
    "STTModelLoaded",
    "STTModelUnloaded",
    "STTService",
    "STTState",
    "STTStateChanged",
    "SpeechSegmentBuffer",
    "TranscriptSegment",
    "TranscriptionCancelled",
    "TranscriptionCompleted",
    "TranscriptionFailed",
    "TranscriptionResult",
    "TranscriptionStarted",
]
