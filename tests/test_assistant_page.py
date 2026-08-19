"""Unit tests for AssistantPage, AIRequestWorker background execution, and voice synchronization."""

from unittest.mock import MagicMock

from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.result import ToolResult
from app.ui.navigation.pages.assistant_page import AIRequestWorker, AssistantPage
from app.voice.conversation.orchestrating_response_provider import (
    OrchestratingResponseProvider,
)


def test_ai_request_worker_direct_run(qapp):
    """Test AIRequestWorker directly runs and emits finished signal."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="system.open_application",
        success=True,
        result_data={"launched": True, "application": "calc.exe"},
    )
    container = MagicMock()
    provider = OrchestratingResponseProvider(ai_orchestrator=MagicMock(tool_executor=executor))
    container.orchestrating_response_provider.return_value = provider
    container.tts_service.return_value = MagicMock()

    worker = AIRequestWorker(
        prompt="Open Calculator",
        executor=executor,
        container=container,
    )

    results = []
    worker.finished.connect(lambda r: results.append(r))
    worker.run()

    assert len(results) == 1
    assert "Opening Calculator now." in results[0]["response"]
    assert results[0]["success"] is True


def test_assistant_page_worker_retention(qapp):
    """Test AssistantPage retains background workers in _active_workers list."""
    page = AssistantPage()
    assert hasattr(page, "_active_workers")
    assert isinstance(page._active_workers, list)

    worker = AIRequestWorker(prompt="help")
    page._run_in_background_thread(worker)

    # Worker should be retained in _active_workers
    assert worker in page._active_workers


def test_assistant_page_acoustic_echo_word_overlap_suppression(qapp):
    """Test AssistantPage suppresses incoming transcriptions with significant word overlap to recent speech."""
    page = AssistantPage()
    page._recent_spoken_phrases = [
        "I attempted to open Microsoft Store, but encountered an error: Application 'microsoft store' could not be resolved or launched: [WinError 2] The system cannot find the file specified: 'microsoft store'"
    ]

    # STT mishearing "WinError 2" as "When air to"
    transcription = "When air to the system cannot find the file specified, Microsoft Store."

    executed = []
    page._run_in_background_thread = lambda worker: executed.append(worker.prompt)

    page._on_eventbus_transcription(transcription)
    # Should be suppressed by word overlap filter and not executed
    assert len(executed) == 0


def test_assistant_page_known_echo_phrase_suppression(qapp):
    """Test AssistantPage suppresses known echo phrases like 'mock response' or 'initialized and active'."""
    page = AssistantPage()

    executed = []
    page._run_in_background_thread = lambda worker: executed.append(worker.prompt)

    page._on_eventbus_transcription("The mock response to the mock response to response.")
    assert len(executed) == 0

    page._on_eventbus_transcription("Friday AI Assistant is initialized and active.")
    assert len(executed) == 0

