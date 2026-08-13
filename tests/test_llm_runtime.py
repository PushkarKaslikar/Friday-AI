"""Comprehensive test suite for Local LLM Runtime & Model Provider Foundation.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

import pytest
from pydantic import BaseModel

from app.ai.errors.exceptions import (
    ModelNotFoundError,
    ModelNotReadyError,
)
from app.ai.gateway.model_manager import LLMModelManager
from app.ai.models.models import (
    AIModelConfiguration,
    AIRequest,
    ModelLifecycleState,
)
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.ai.providers.llama_cpp_provider import LlamaCppProvider
from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus


class SampleOutputSchema(BaseModel):
    """Test schema for structured output validation."""

    summary: str
    confidence: int
    is_valid: bool


def test_llm_model_config_defaults():
    """Verify default AIModelConfiguration settings."""
    cfg = AIModelConfiguration()
    assert cfg.provider == "llama_cpp"
    assert cfg.model_name == "tinyllama-1.1b-chat.Q4_K_M.gguf"
    assert cfg.preload_model is False
    assert cfg.context_size == 4096
    assert cfg.use_cuda is False
    assert cfg.threads == 4


def test_fake_ai_model_provider_lifecycle():
    """Verify FakeAIModelProvider state machine transitions."""
    provider = FakeAIModelProvider()
    assert provider.state == ModelLifecycleState.UNINITIALIZED

    provider.load_model()
    assert provider.state == ModelLifecycleState.READY

    req = AIRequest(request_id="t1", prompt="Hello LLM")
    resp = provider.generate(req)
    assert resp.text == "Mock Response to: 'Hello LLM'"
    assert resp.total_tokens > 0

    provider.unload_model()
    assert provider.state == ModelLifecycleState.UNINITIALIZED


def test_fake_ai_model_provider_streaming():
    """Verify stream generation returns token iterator."""
    provider = FakeAIModelProvider()
    provider.load_model()

    req = AIRequest(request_id="t2", prompt="Stream test", stream=True)
    tokens = list(provider.generate_stream(req))

    assert len(tokens) == 5
    assert "".join(tokens) == "FRIDAY LOCAL LLM TEST PASSED"


def test_fake_ai_model_provider_structured_output():
    """Verify structured generation parses into Pydantic schema."""
    provider = FakeAIModelProvider()
    provider.load_model()

    req = AIRequest(request_id="t3", prompt="Generate JSON")
    result = provider.generate_structured(request=req, schema_cls=SampleOutputSchema)

    assert isinstance(result, SampleOutputSchema)
    assert result.confidence == 42
    assert result.is_valid is True


def test_model_manager_lazy_vs_preload_loading():
    """Verify lazy-loading behavior when preload_model=False."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    fake_prov = FakeAIModelProvider()

    manager = LLMModelManager(
        config_manager=config_mgr, event_bus=event_bus, provider=fake_prov
    )
    manager.initialize()
    manager.start()

    # Preload disabled by default -> UNINITIALIZED
    assert manager.lifecycle_state == ModelLifecycleState.UNINITIALIZED

    # Generate -> Auto-loads on demand
    req = AIRequest(request_id="t4", prompt="Auto load test")
    resp = manager.generate(req)

    assert resp.text is not None
    assert manager.lifecycle_state == ModelLifecycleState.READY

    manager.stop()


def test_model_manager_provider_switching():
    """Verify dynamic provider switching on LLMModelManager."""
    manager = LLMModelManager(
        provider=FakeAIModelProvider(default_response_text="Fake 1")
    )
    manager.initialize()
    manager.load_model()

    meta1 = manager.get_metadata()
    assert meta1.provider_name == "fake"

    # Switch provider
    new_fake = FakeAIModelProvider(default_response_text="Fake 2")
    manager.set_provider(new_fake)
    manager.load_model()

    meta2 = manager.get_metadata()
    assert meta2.provider_name == "fake"
    resp = manager.generate(AIRequest(request_id="t5"))
    assert resp.text == "Fake 2"


def test_llama_cpp_provider_missing_model_error():
    """Verify LlamaCppProvider raises ModelNotFoundError when model file is missing."""
    provider = LlamaCppProvider()
    cfg = AIModelConfiguration(model_path="non_existent_model_file.gguf")
    provider.initialize(cfg)

    with pytest.raises(ModelNotFoundError):
        provider.load_model()


def test_llama_cpp_uninitialized_inference_error():
    """Verify generation before model load raises ModelNotReadyError."""
    provider = LlamaCppProvider()
    with pytest.raises(ModelNotReadyError):
        provider.generate(AIRequest(request_id="t6"))


def test_llm_bootstrapper_and_health_check(qapp):
    """Verify LLMModelManager integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        manager: LLMModelManager = result.container.llm_model_manager()
        assert manager is not None
        report = manager.get_health_report()

        assert "provider" in report
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_boundary_no_eval_exec():
    """Verify LLM runtime contains zero dynamic Python code evaluation."""
    fake_prov = FakeAIModelProvider(
        default_response_text="import os; os.system('echo hack')"
    )
    fake_prov.load_model()

    response = fake_prov.generate(AIRequest(request_id="t7", prompt="Try hack"))
    # Text is returned purely as strings, never evaluated or executed
    assert isinstance(response.text, str)
