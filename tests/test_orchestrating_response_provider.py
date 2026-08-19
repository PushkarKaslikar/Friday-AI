"""Unit test suite for OrchestratingResponseProvider.

Tests that voice transcripts properly trigger tool execution and return spoken confirmation.
"""

from unittest.mock import MagicMock

from app.ai.orchestration.ai_orchestrator import AIOrchestrator
from app.ai.orchestration.models import OrchestrationResult
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.result import ToolResult
from app.tools.registry.tool_registry import ToolRegistry
from app.voice.conversation.orchestrating_response_provider import (
    OrchestratingResponseProvider,
)


def test_orchestrating_provider_empty_input():
    """Verify empty input returns default listening response."""
    orchestrator = MagicMock(spec=AIOrchestrator)
    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("")
    assert "Friday is online" in resp


def test_orchestrating_provider_open_file_explorer_fast_path():
    """Verify 'open file explorer' invokes system.open_application with 'explorer'."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="system.open_application",
        success=True,
        result={"launched": True, "application": "explorer.exe"},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("open file explorer")

    assert "Opening File Explorer now." in resp
    executor.execute.assert_called_once()
    call_kwargs = executor.execute.call_args.kwargs
    assert call_kwargs["tool_id"] == "system.open_application"
    assert call_kwargs["arguments"]["application"] == "explorer"


def test_orchestrating_provider_open_notepad_fast_path():
    """Verify 'open notepad' invokes system.open_application with 'notepad'."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="system.open_application",
        success=True,
        result={"launched": True, "application": "notepad.exe"},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("open notepad")

    assert "Opening Notepad now." in resp
    call_kwargs = executor.execute.call_args.kwargs
    assert call_kwargs["arguments"]["application"] == "notepad"


def test_orchestrating_provider_volume_fast_path():
    """Verify 'set volume to 75' invokes audio.set_volume."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="audio.set_volume",
        success=True,
        result={"volume": 75},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("set volume to 75")

    assert "75 percent" in resp
    call_kwargs = executor.execute.call_args.kwargs
    assert call_kwargs["tool_id"] == "audio.set_volume"
    assert call_kwargs["arguments"]["volume"] == 75


def test_orchestrating_provider_mute_fast_path():
    """Verify 'mute audio' invokes audio.mute."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="audio.mute",
        success=True,
        result={"is_muted": True},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("mute audio")

    assert "muted" in resp
    call_kwargs = executor.execute.call_args.kwargs
    assert call_kwargs["tool_id"] == "audio.mute"


def test_orchestrating_provider_ai_fallback():
    """Verify general conversational query falls back to AIOrchestrator."""
    executor = MagicMock(spec=ToolExecutor)
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor
    orchestrator.process_request.return_value = OrchestrationResult(
        request_id="voice-test",
        final_response="Paris is the capital of France.",
        success=True,
    )

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("What is the capital of France?")

    assert resp == "Paris is the capital of France."
    orchestrator.process_request.assert_called_once()


def test_orchestrating_provider_open_calculator_fast_path():
    """Verify 'open calculator' and 'open calculate' invoke system.open_application with 'calc'."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="system.open_application",
        success=True,
        result_data={"launched": True, "application": "calc.exe"},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("Open Calculator")

    assert "Opening Calculator now." in resp
    executor.execute.assert_called_once()
    call_kwargs = executor.execute.call_args.kwargs
    assert call_kwargs["tool_id"] == "system.open_application"
    assert call_kwargs["arguments"]["application"] == "calc"

    executor.reset_mock()
    resp_calc = provider.get_response("Open Calculate")
    assert "Opening Calculator now." in resp_calc
    call_kwargs_2 = executor.execute.call_args.kwargs
    assert call_kwargs_2["arguments"]["application"] == "calc"


def test_orchestrating_provider_screenshot_fast_path():
    """Verify 'take screenshot' invokes screen.capture."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="screen.capture",
        success=True,
        result_data={"width": 1920, "height": 1080},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("take a screenshot")

    assert "Screen capture completed" in resp
    executor.execute.assert_called_once()
    assert executor.execute.call_args.kwargs["tool_id"] == "screen.capture"


def test_orchestrating_provider_list_windows_fast_path():
    """Verify 'list open windows' invokes window.list_open."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute.return_value = ToolResult(
        tool_id="window.list_open",
        success=True,
        result_data={"windows": [{"title": "Friday AI", "hwnd": 12345}]},
    )
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.tool_executor = executor

    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)
    resp = provider.get_response("list open windows")

    assert "Friday found 1 open windows" in resp
    executor.execute.assert_called_once()
    assert executor.execute.call_args.kwargs["tool_id"] == "window.list_open"


def test_orchestrating_provider_greetings_fast_path():
    """Verify 'Friday' and 'who are you' return immediate assistance responses without LLM."""
    orchestrator = MagicMock(spec=AIOrchestrator)
    provider = OrchestratingResponseProvider(ai_orchestrator=orchestrator)

    resp_friday = provider.get_response("Friday")
    assert "Hello! I am Friday" in resp_friday

    resp_who = provider.get_response("Who are you?")
    assert "personal AI assistant" in resp_who

