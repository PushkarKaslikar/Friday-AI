"""Comprehensive test suite for AI Orchestrator & Reasoning Engine.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

from pydantic import BaseModel

from app.ai.gateway.model_manager import LLMModelManager
from app.ai.orchestration.ai_orchestrator import AIOrchestrator
from app.ai.orchestration.models import (
    OrchestrationRequest,
    OrchestratorConfiguration,
)
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.tools.base.metadata import ToolCategory, ToolMetadata
from app.tools.base.tool import BaseTool
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.result import ToolResult
from app.tools.registry.tool_registry import ToolRegistry


class DummyEchoInput(BaseModel):
    message: str = "Friday Test"


class DummyEchoTool(BaseTool):
    """Dummy echo tool for orchestration workflow testing."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            tool_id="echo_tool",
            name="echo_tool",
            display_name="Echo Tool",
            description="Echo back input message.",
            category=ToolCategory.UTILITY,
            input_schema=DummyEchoInput,
        )
        super().__init__(metadata)

    def run_tool(self, validated_input: BaseModel, command_id: str = "") -> Any:
        inp: DummyEchoInput = validated_input  # type: ignore
        return {"echoed": inp.message}


def test_orchestrator_config_defaults():
    """Verify default OrchestratorConfiguration settings."""
    cfg = OrchestratorConfiguration()
    assert cfg.enabled is True
    assert cfg.max_steps == 5
    assert cfg.allow_tools is True


def test_orchestrator_direct_response_flow():
    """Verify single-turn direct text response flow without tool calls."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    fake_llm = FakeAIModelProvider(
        default_response_text='{"response": "Hello! How can I assist you today?"}'
    )
    llm_manager = LLMModelManager(
        config_manager=config_mgr, event_bus=event_bus, provider=fake_llm
    )
    llm_manager.load_model()

    orchestrator = AIOrchestrator(
        config_manager=config_mgr,
        event_bus=event_bus,
        llm_manager=llm_manager,
    )
    orchestrator.initialize()
    orchestrator.start()

    req = OrchestrationRequest(request_id="req-01", user_input="Hello Friday")
    res = orchestrator.process_request(req)

    assert res.success is True
    assert "Hello!" in res.final_response
    assert res.turns_taken == 1
    assert len(res.executed_tools) == 0

    orchestrator.stop()


def test_orchestrator_tool_call_flow():
    """Verify multi-step tool call execution and synthesis flow."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    registry = ToolRegistry(event_bus=event_bus)
    registry.clear()
    echo_tool = DummyEchoTool()
    registry.register_tool(echo_tool)

    executor = ToolExecutor(registry=registry, event_bus=event_bus)
    executor.initialize()
    executor.start()

    # Simulate 2-turn response: Turn 1 requests echo_tool, Turn 2 gives final text
    turn1_json = '{"tool_call": {"name": "echo_tool", "arguments": {"message": "Friday Test"}}, "reasoning": "Need to echo text"}'
    turn2_json = '{"response": "Successfully echoed your text: Friday Test", "reasoning": "Completed tool execution"}'

    class MultiTurnFakeProvider(FakeAIModelProvider):
        def __init__(self):
            super().__init__()
            self.turn_count = 0

        def generate(self, request):
            self.turn_count += 1
            text = turn1_json if self.turn_count == 1 else turn2_json
            return (
                super()
                .generate(request)
                .__class__(
                    request_id=request.request_id,
                    text=text,
                    finish_reason="stop",
                    prompt_tokens=10,
                    completion_tokens=10,
                    total_tokens=20,
                    tokens_per_second=100.0,
                    generation_duration_ms=10.0,
                )
            )

    fake_llm = MultiTurnFakeProvider()
    llm_manager = LLMModelManager(
        config_manager=config_mgr, event_bus=event_bus, provider=fake_llm
    )
    llm_manager.load_model()

    orchestrator = AIOrchestrator(
        config_manager=config_mgr,
        event_bus=event_bus,
        llm_manager=llm_manager,
        tool_executor=executor,
        tool_registry=registry,
    )
    orchestrator.initialize()
    orchestrator.start()

    req = OrchestrationRequest(
        request_id="req-02", user_input="Echo the phrase Friday Test"
    )
    res = orchestrator.process_request(req)

    assert res.success is True
    assert len(res.executed_tools) == 1
    assert res.executed_tools[0]["tool_name"] == "echo_tool"
    assert res.executed_tools[0]["success"] is True
    assert "echoed" in res.executed_tools[0]["result"]
    assert res.executed_tools[0]["result"]["echoed"] == "Friday Test"
    assert "Successfully echoed" in res.final_response

    executor.stop()
    orchestrator.stop()


def test_orchestrator_unregistered_tool_error_handling():
    """Verify Orchestrator handles requests for non-existent tools gracefully."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    registry = ToolRegistry(event_bus=event_bus)

    # LLM attempts to call an invalid tool name
    invalid_tool_json = '{"tool_call": {"name": "non_existent_tool", "arguments": {}}, "reasoning": "Invalid tool test"}'
    fake_llm = FakeAIModelProvider(default_response_text=invalid_tool_json)
    llm_manager = LLMModelManager(
        config_manager=config_mgr, event_bus=event_bus, provider=fake_llm
    )
    llm_manager.load_model()

    orchestrator = AIOrchestrator(
        config_manager=config_mgr,
        event_bus=event_bus,
        llm_manager=llm_manager,
        tool_registry=registry,
    )
    orchestrator.initialize()
    orchestrator.start()

    req = OrchestrationRequest(
        request_id="req-03", user_input="Do invalid action", max_steps=2
    )
    res = orchestrator.process_request(req)

    assert res.success is True
    assert res.turns_taken == 2
    orchestrator.stop()


def test_orchestrator_bootstrapper_integration(qapp):
    """Verify AIOrchestrator integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        orchestrator: AIOrchestrator = result.container.ai_orchestrator()
        assert orchestrator is not None
        report = orchestrator.get_health_report()

        assert "status" in report
        assert "metrics" in report
        assert report["subsystem"] == "AI Orchestrator & Reasoning Workflow Engine"
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_boundary_no_eval_exec():
    """Verify orchestrator performs zero dynamic code evaluation (eval/exec)."""
    orchestrator = AIOrchestrator()
    # Code inspection verification that eval/exec are not imported or invoked
    import inspect

    source = inspect.getsource(orchestrator.__class__)
    assert "eval(" not in source
    assert "exec(" not in source
