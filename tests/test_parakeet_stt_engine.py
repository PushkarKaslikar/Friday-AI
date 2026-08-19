"""Unit test suite for ParakeetTDTSTTEngine and Parakeet integration in STTService."""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from app.voice.stt.models import STTConfiguration, TranscriptionResult
from app.voice.stt.parakeet_tdt_engine import ParakeetTDTSTTEngine
from app.voice.stt.stt_service import STTService


def test_parakeet_engine_initialization_defaults():
    """Verify Parakeet engine initializes with expected default configuration."""
    cfg = STTConfiguration(model_name="nvidia/parakeet-tdt-0.6b-v3", device="cpu")
    engine = ParakeetTDTSTTEngine(config=cfg)

    assert engine.config.model_name == "nvidia/parakeet-tdt-0.6b-v3"
    assert engine.is_loaded is False
    assert engine.actual_device == "cpu"
    assert engine.actual_compute_type == "float32"


def test_parakeet_engine_short_audio_rejection():
    """Verify audio samples shorter than 0.1s return TOO_SHORT without calling model."""
    engine = ParakeetTDTSTTEngine()
    engine._is_loaded = True
    engine._model = MagicMock()
    engine._processor = MagicMock()

    short_audio = np.zeros(100, dtype=np.float32)  # 100 samples at 16kHz = ~0.006s
    res = engine.transcribe(short_audio, sample_rate=16000)

    assert res.status == "TOO_SHORT"
    assert res.text == ""
    assert res.duration_seconds < 0.1
    engine._processor.assert_not_called()


def test_parakeet_engine_unloaded_transcribe_fails_gracefully():
    """Verify calling transcribe when unloaded returns FAILED status gracefully."""
    engine = ParakeetTDTSTTEngine()
    assert engine.is_loaded is False

    audio = np.zeros(16000, dtype=np.float32)
    res = engine.transcribe(audio, sample_rate=16000)

    assert res.status == "FAILED"
    assert "not loaded" in res.metadata.get("error", "")


def test_parakeet_engine_mock_transcribe_success():
    """Verify successful transcription inference and result metrics calculation."""
    engine = ParakeetTDTSTTEngine()
    engine._is_loaded = True
    engine._actual_device = "cpu"
    engine._actual_compute_type = "float32"

    mock_processor = MagicMock()
    mock_processor.return_value = {"input_features": MagicMock()}
    mock_processor.batch_decode.return_value = ["Open File Explorer"]

    mock_model = MagicMock()
    mock_output = MagicMock()
    mock_model.return_value = mock_output

    engine._processor = mock_processor
    engine._model = mock_model

    # 1 second of mock audio
    audio = np.random.randn(16000).astype(np.float32)

    with patch("app.voice.stt.parakeet_tdt_engine.torch") as mock_torch:
        mock_torch.argmax.return_value = MagicMock()
        res = engine.transcribe(audio, sample_rate=16000)

    assert res.status == "SUCCESS"
    assert res.text == "Open File Explorer"
    assert res.duration_seconds == pytest.approx(1.0, 0.05)
    assert res.processing_time_seconds >= 0.0


def test_parakeet_engine_unload():
    """Verify unload_model cleans up references."""
    engine = ParakeetTDTSTTEngine()
    engine._is_loaded = True
    engine._model = MagicMock()
    engine._processor = MagicMock()

    engine.unload_model()
    assert engine.is_loaded is False
    assert engine._model is None
    assert engine._processor is None


def test_stt_service_instantiates_parakeet_when_configured():
    """Verify STTService selects ParakeetTDTSTTEngine when configured."""
    config_mgr = MagicMock()
    config_mgr.settings.stt.enabled = True
    config_mgr.settings.stt.engine = "parakeet"
    config_mgr.settings.stt.model_name = "nvidia/parakeet-tdt-0.6b-v3"
    config_mgr.settings.stt.device = "auto"
    config_mgr.settings.stt.compute_type = "auto"
    config_mgr.settings.stt.language = None
    config_mgr.settings.stt.beam_size = 5
    config_mgr.settings.stt.max_segment_duration_ms = 30000.0
    config_mgr.settings.stt.word_timestamps = False
    config_mgr.settings.stt.vad_filter = False
    config_mgr.settings.stt.custom_model_path = None

    service = STTService(config_manager=config_mgr)
    assert isinstance(service.engine, ParakeetTDTSTTEngine)


def test_stt_service_discards_speech_when_speaker_active():
    """Verify STTService discards speech segments and ignores frames when speaker is active."""
    audio_engine = MagicMock()
    audio_engine.is_playing_audio = True

    service = STTService(audio_engine=audio_engine)
    service._is_listening = True

    # SpeechStarted should be ignored
    service.speech_buffer.start_collection = MagicMock()
    service._on_speech_started(MagicMock())
    service.speech_buffer.start_collection.assert_not_called()

    # SpeechStopped should clear buffer and not submit jobs
    service._executor = MagicMock()
    service._on_speech_stopped(MagicMock())
    service._executor.submit.assert_not_called()

