"""Comprehensive test suite for Dynamic Response Generation Engine.

Phase 4.5 - Dynamic Response Generation Engine
"""

from app.ai.personality.models import EmotionalSignal, PersonalityContext
from app.ai.response.context_builder import ResponseContextBuilder
from app.ai.response.models import (
    ResponseGenerationMode,
    ResponseGenerationRequest,
    ResponseStatus,
)
from app.ai.response.response_generator import ResponseGenerator
from app.ai.response.strategy_selector import ResponseStrategySelector
from app.ai.response.validator_normalizer import ResponseValidatorNormalizer
from app.bootstrap.bootstrapper import AppBootstrapper


def test_determine_factual_status():
    """Verify factual status mapping from tool execution results."""
    builder = ResponseContextBuilder()

    # 1. No tool results -> SUCCESS
    assert builder.determine_factual_status([]) == ResponseStatus.SUCCESS

    # 2. Tool success -> SUCCESS
    assert (
        builder.determine_factual_status([{"status": "SUCCESS"}])
        == ResponseStatus.SUCCESS
    )

    # 3. Tool failure -> FAILED
    assert (
        builder.determine_factual_status([{"status": "FAILED"}])
        == ResponseStatus.FAILED
    )

    # 4. Partial success -> PARTIAL_SUCCESS
    assert (
        builder.determine_factual_status([{"status": "SUCCESS"}, {"status": "FAILED"}])
        == ResponseStatus.PARTIAL_SUCCESS
    )

    # 5. Authorization denial -> DENIED
    assert (
        builder.determine_factual_status([{"status": "AUTHORIZATION_DENIED"}])
        == ResponseStatus.DENIED
    )


def test_build_prompt_context_sanitization():
    """Verify context builder masks secrets and formats TOOL_RESULT tags."""
    builder = ResponseContextBuilder()
    req = ResponseGenerationRequest(
        request_id="req-1",
        user_input="Get API token",
        tool_results=[
            {
                "tool_name": "auth.get",
                "status": "SUCCESS",
                "result": {"api_key": "SECRET_KEY_123"},
            }
        ],
    )
    prompt = builder.build_prompt_context(req)

    assert '<TOOL_RESULT idx="1" tool_name="auth.get" status="SUCCESS">' in prompt
    assert "SECRET_KEY_123" not in prompt
    assert "********" in prompt


def test_response_strategy_selector():
    """Verify strategy selector adapts parameters under frustration or error mode."""
    selector = ResponseStrategySelector()
    pers_ctx = PersonalityContext(
        identity_name="Friday",
        role="Assistant",
        style_mode="NORMAL",
        emotional_signal=EmotionalSignal.FRUSTRATED,
        effective_formality=0.6,
        effective_humor=0.05,
        effective_emotional_responsiveness=0.9,
        effective_proactivity=0.4,
        effective_conciseness=0.85,
        system_prompt_snippet="Be helpful.",
    )

    req = ResponseGenerationRequest(
        request_id="req-2",
        user_input="Broken app",
        personality_context=pers_ctx,
        response_mode=ResponseGenerationMode.ERROR,
    )
    strat = selector.select_strategy(req, ResponseStatus.FAILED)

    assert strat["mode"] == ResponseGenerationMode.ERROR.value
    assert strat["include_next_step"] is True
    assert "empathetic" in strat["style_instruction"]


def test_validator_normalizer_cleaning():
    """Verify stripping markdown code blocks, leaked prompts, and formatting TTS text."""
    vn = ResponseValidatorNormalizer()

    # Test 1: Validation leakage check
    is_valid, err = vn.validate_raw_response(
        "Here is instructions: ### SYSTEM INSTRUCTIONS hello"
    )
    assert is_valid is False
    assert "leaked" in err

    # Test 2: Normalization strip code blocks
    clean, spoken = vn.normalize('```json\n{"response": "Chrome is open."}\n```')
    assert clean == "Chrome is open."
    assert spoken == "Chrome is open."


def test_factual_grounding_preserves_failures():
    """Verify tool failures yield FAILED status and error messaging."""
    engine = ResponseGenerator()
    req = ResponseGenerationRequest(
        request_id="req-3",
        user_input="Open App",
        tool_results=[
            {"tool_name": "system.open", "status": "FAILED", "error": "File not found"}
        ],
    )
    res = engine.generate_response(req)

    assert res.status == ResponseStatus.FAILED
    assert (
        "couldn't" in res.response_text.lower() or "failed" in res.response_text.lower()
    )


def test_deterministic_fallback_on_llm_failure():
    """Verify deterministic fallback response when LLM throws exception or times out."""
    engine = ResponseGenerator()
    req = ResponseGenerationRequest(
        request_id="req-4",
        user_input="Perform backup",
        tool_results=[{"tool_name": "backup.create", "status": "SUCCESS"}],
    )
    res = engine.format_fallback_response(req, "Simulated LLM Failure")

    assert res.status == ResponseStatus.FALLBACK_USED
    assert res.metadata.fallback_used is True
    assert "Done" in res.response_text or "completed" in res.response_text


def test_bootstrapper_integration_and_health_check(qapp):
    """Verify ResponseGenerator integration into AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        engine: ResponseGenerator = result.container.response_generator()
        assert engine is not None
        report = engine.get_health_report()

        assert report["subsystem"] == "Dynamic Response Generation Engine"
        assert report["status"] == "HEALTHY"
        assert report["streaming_enabled"] is True
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_boundary_no_eval_exec_or_tool_execution():
    """Verify ResponseGenerator contains zero tool execution authority and zero eval/exec code evaluation."""
    engine = ResponseGenerator()
    import inspect

    source = inspect.getsource(engine.__class__)
    assert "eval(" not in source
    assert "exec(" not in source
    assert not hasattr(engine, "execute_tool")
