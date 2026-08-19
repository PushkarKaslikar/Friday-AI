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
