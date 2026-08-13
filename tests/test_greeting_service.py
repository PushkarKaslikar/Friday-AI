"""Comprehensive test suite for Natural Greetings Foundation Subsystem.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.greeting.events import (
    GreetingGenerated,
    GreetingGenerationFailed,
    GreetingSkipped,
)
from app.voice.greeting.greeting_context_builder import GreetingContextBuilder
from app.voice.greeting.greeting_selector import GreetingSelector
from app.voice.greeting.greeting_service import GreetingService
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingConfiguration,
    GreetingContext,
    GreetingStyle,
    TimeOfDay,
)
from app.voice.greeting.template_provider import TemplateGreetingProvider


def test_greeting_config_defaults():
    """Verify default GreetingConfiguration values."""
    cfg = GreetingConfiguration()
    assert cfg.enabled is True
    assert cfg.max_recent_history == 5
    assert cfg.avoid_repetition is True
    assert cfg.default_style == GreetingStyle.FRIDAY
    assert cfg.use_context is True


def test_time_of_day_classification():
    """Verify time of day hour classification boundaries."""
    assert GreetingContextBuilder.get_time_of_day(8) == TimeOfDay.MORNING
    assert GreetingContextBuilder.get_time_of_day(14) == TimeOfDay.AFTERNOON
    assert GreetingContextBuilder.get_time_of_day(19) == TimeOfDay.EVENING
    assert GreetingContextBuilder.get_time_of_day(23) == TimeOfDay.NIGHT
    assert GreetingContextBuilder.get_time_of_day(3) == TimeOfDay.NIGHT


def test_template_greeting_provider_categories():
    """Verify TemplateGreetingProvider selects context-aware categories."""
    provider = TemplateGreetingProvider()

    # Morning
    ctx_morning = GreetingContext(
        session_id="s1", time_of_day=TimeOfDay.MORNING, is_new_session=True
    )
    resp_m = provider.generate_greeting(ctx_morning)
    assert resp_m.category == GreetingCategory.MORNING
    assert len(resp_m.text) > 0

    # Afternoon
    ctx_afternoon = GreetingContext(
        session_id="s2", time_of_day=TimeOfDay.AFTERNOON, is_new_session=True
    )
    resp_a = provider.generate_greeting(ctx_afternoon)
    assert resp_a.category == GreetingCategory.AFTERNOON

    # Evening
    ctx_evening = GreetingContext(
        session_id="s3", time_of_day=TimeOfDay.EVENING, is_new_session=True
    )
    resp_e = provider.generate_greeting(ctx_evening)
    assert resp_e.category == GreetingCategory.EVENING

    # Returning Session
    ctx_ret = GreetingContext(session_id="s4", is_returning_session=True, turn_count=3)
    resp_r = provider.generate_greeting(ctx_ret)
    assert resp_r.category == GreetingCategory.RETURNING


def test_greeting_repetition_prevention():
    """Verify GreetingSelector avoids immediate repetition of identical greetings."""
    selector = GreetingSelector(config=GreetingConfiguration(max_recent_history=3))
    candidates = ["Greeting A", "Greeting B", "Greeting C"]

    f1 = selector.filter_candidates(candidates)
    assert len(f1) == 3

    selector.record_selected_greeting("Greeting A")
    f2 = selector.filter_candidates(candidates)
    assert "Greeting A" not in f2
    assert len(f2) == 2


def test_greeting_service_generate_greeting():
    """Verify GreetingService generation workflow and event bus integration."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    service = GreetingService(config_manager=config_mgr, event_bus=event_bus)
    service.initialize()
    service.start()

    events_generated = []
    event_bus.subscribe(GreetingGenerated, lambda e: events_generated.append(e))

    sess_id = "test-greeting-sess-1"
    response = service.generate_greeting(sess_id, activation_source="DOUBLE_CLAP")

    assert response.should_speak is True
    assert len(response.text) > 0
    assert len(events_generated) == 1
    assert events_generated[0].session_id == sess_id

    service.stop()


def test_greeting_disabled():
    """Verify disabled greetings skip generation safely."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    service = GreetingService(config_manager=config_mgr, event_bus=event_bus)
    service._greeting_config.enabled = False
    service.initialize()
    service.start()

    events_skipped = []
    event_bus.subscribe(GreetingSkipped, lambda e: events_skipped.append(e))

    response = service.generate_greeting("sess-disabled")
    assert response.should_speak is False
    assert len(events_skipped) == 1
    assert events_skipped[0].reason == "greetings_disabled"

    service.stop()


class FaultyProvider:
    """Mock provider raising exception for error testing."""

    @property
    def provider_name(self):
        return "FaultyProvider"

    def generate_greeting(self, context):
        raise RuntimeError("Provider failed intentionally")


def test_greeting_provider_failure_fallback():
    """Verify provider exception falls back cleanly to 'How can I help?' without crashing."""
    event_bus = EventBus()
    service = GreetingService(event_bus=event_bus, provider=FaultyProvider())
    service.initialize()
    service.start()

    events_failed = []
    event_bus.subscribe(GreetingGenerationFailed, lambda e: events_failed.append(e))

    response = service.generate_greeting("sess-error-1")
    assert response.text == "How can I help?"
    assert response.category == GreetingCategory.FALLBACK
    assert len(events_failed) == 1
    assert events_failed[0].fallback_used is True

    service.stop()


def test_greeting_bootstrapper_integration(qapp):
    """Verify GreetingService integration in 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        svc: GreetingService = result.container.greeting_service()
        assert svc is not None
        report = svc.get_health_report()

        assert report["provider"] == "GreetingService (TemplateGreetingProvider)"
        assert report["status"] == "HEALTHY"
        assert report["enabled"] is True
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_all_voice_services_coexistence(qapp):
    """Verify all voice services Phase 3.1 - Phase 3.9 coexist cleanly."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        g_svc = result.container.greeting_service()
        c_mgr = result.container.conversation_manager()
        c_sm = result.container.conversation_state_machine()

        assert g_svc.is_running is True
        assert c_mgr.is_running is True
        assert c_sm.is_running is True
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
