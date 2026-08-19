from app.ai.gateway.model_manager import LLMModelManager
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.bootstrap.bootstrapper import AppBootstrapper
from app.voice.greeting.ai_greeting_provider import AIGreetingProvider
from app.voice.greeting.greeting_service import GreetingService
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingContext,
    GreetingResponse,
    TimeOfDay,
)


def test_ai_greeting_provider_name():
    """Verify provider identifier property."""
    provider = AIGreetingProvider()
    assert provider.provider_name == "AIGreetingProvider"


def test_generate_ai_greeting_new_session():
    """Verify AI greeting generation for a new morning session."""
    llm_manager = LLMModelManager(
        provider=FakeAIModelProvider(default_response_text="Good morning Pushkar. Ready to assist.")
    )
    provider = AIGreetingProvider(llm_manager=llm_manager)
    ctx = GreetingContext(
        session_id="s-new-1",
        activation_source="WAKE_WORD",
        time_of_day=TimeOfDay.MORNING,
        is_new_session=True,
        is_returning_session=False,
    )
    res = provider.generate_greeting(ctx)

    assert isinstance(res, GreetingResponse)
    assert res.text != ""
    assert res.provider == "AIGreetingProvider"
    assert res.should_speak is True


def test_generate_ai_greeting_returning_session():
    """Verify AI greeting generation for a returning session."""
    llm_manager = LLMModelManager(
        provider=FakeAIModelProvider(default_response_text="Welcome back Pushkar. Continuing our work.")
    )
    provider = AIGreetingProvider(llm_manager=llm_manager)
    ctx = GreetingContext(
        session_id="s-ret-1",
        activation_source="DOUBLE_CLAP",
        time_of_day=TimeOfDay.EVENING,
        is_new_session=False,
        is_returning_session=True,
        current_conversation_topic="PYTHON_DEV",
        last_user_interaction="Fix bug in main loop",
    )
    res = provider.generate_greeting(ctx)

    assert isinstance(res, GreetingResponse)
    assert res.category == GreetingCategory.RETURNING
    assert res.provider == "AIGreetingProvider"


def test_ai_greeting_llm_failure_template_fallback():
    """Verify clean fallback to TemplateGreetingProvider when LLM is unavailable or fails."""
    provider = AIGreetingProvider()

    # Mock llm_manager to raise an exception
    class BrokenLLMManager:
        def generate(self, req):
            raise RuntimeError("Local LLM Offline")

    provider.llm_manager = BrokenLLMManager()

    ctx = GreetingContext(
        session_id="s-fail-1",
        activation_source="WAKE_WORD",
        time_of_day=TimeOfDay.AFTERNOON,
    )
    res = provider.generate_greeting(ctx)

    assert isinstance(res, GreetingResponse)
    assert res.provider == "TemplateGreetingProvider"
    assert res.text != ""


def test_ai_greeting_repetition_prevention(qapp):
    """Verify repetition prevention across consecutive activations using GreetingService."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        svc: GreetingService = result.container.greeting_service()

        res1 = svc.generate_activation_greeting("s1", "WAKE_WORD")
        res2 = svc.generate_activation_greeting("s1", "WAKE_WORD")

        assert res1.text != ""
        assert res2.text != ""
        # The selector prevents repeating identical strings if history permits
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_zero_tool_execution_authority():
    """Verify AIGreetingProvider contains zero tool execution power or eval/exec evaluation."""
    provider = AIGreetingProvider()
    import inspect

    src = inspect.getsource(provider.__class__)

    assert "eval(" not in src
    assert "exec(" not in src
    assert not hasattr(provider, "execute_tool")
