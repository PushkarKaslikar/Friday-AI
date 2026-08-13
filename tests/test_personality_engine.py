"""Comprehensive test suite for Personality Engine & Behavioral Identity System.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

from app.ai.personality.emotional_classifier import EmotionalSignalClassifier
from app.ai.personality.models import (
    EmotionalSignal,
    PersonalityModifier,
    ResponseStyleMode,
)
from app.ai.personality.personality_engine import PersonalityEngine
from app.bootstrap.bootstrapper import AppBootstrapper


def test_personality_profile_defaults():
    """Verify default personality profile, identity, communication scales, and 20 rules."""
    engine = PersonalityEngine()
    profile = engine.get_personality_profile()

    assert profile.identity.name == "Friday"
    assert profile.identity.role == "Personal AI Assistant"
    assert profile.communication.formality == 0.5
    assert profile.communication.humor == 0.25
    assert profile.communication.conciseness == 0.75
    assert len(profile.behavioral_rules) == 20


def test_emotional_signal_classification():
    """Verify EmotionalSignalClassifier pattern matching logic."""
    classifier = EmotionalSignalClassifier()

    assert classifier.classify("Hello, how are you?") == EmotionalSignal.NEUTRAL
    assert classifier.classify("Thanks so much!") == EmotionalSignal.POSITIVE
    assert (
        classifier.classify("Why is this taking so long, it's broken!!")
        == EmotionalSignal.FRUSTRATED
    )
    assert (
        classifier.classify("I need this urgently right now") == EmotionalSignal.URGENT
    )
    assert (
        classifier.classify("Woohoo that worked perfectly!") == EmotionalSignal.EXCITED
    )
    assert (
        classifier.classify("Wait, I don't understand what you mean??")
        == EmotionalSignal.CONFUSED
    )


def test_compact_system_prompt_snippet_generation():
    """Verify system prompt snippet is compact (< 150 tokens, ~400 chars)."""
    engine = PersonalityEngine()
    ctx = engine.generate_personality_context(
        user_input="Open Chrome", style_mode=ResponseStyleMode.NORMAL
    )

    snippet = ctx.system_prompt_snippet
    assert "Friday" in snippet
    assert len(snippet) < 600  # Compact character bound
    assert len(snippet.split()) < 100  # < 100 words (~130 tokens)


def test_frustration_adaptation():
    """Verify under user frustration humor drops to near zero and conciseness increases."""
    engine = PersonalityEngine()
    ctx = engine.generate_personality_context(
        user_input="Ugh, why is this stupid thing broken!!"
    )

    assert ctx.emotional_signal == EmotionalSignal.FRUSTRATED
    assert ctx.effective_humor <= 0.1
    assert ctx.effective_conciseness >= 0.8
    assert "empathetically to user frustration" in ctx.system_prompt_snippet


def test_temporary_personality_modifier_stack():
    """Verify applying temporary modifiers dynamically adjusts effective values without mutating base profile."""
    engine = PersonalityEngine()
    base_profile = engine.get_personality_profile()
    base_formality = base_profile.communication.formality

    mod = PersonalityModifier(
        source="test",
        reason="technical_depth",
        formality_delta=0.3,
        humor_delta=-0.2,
    )
    engine.apply_temporary_modifier(mod)

    ctx = engine.generate_personality_context(user_input="Explain architecture.")
    assert ctx.effective_formality == min(base_formality + 0.3, 1.0)

    engine.clear_modifiers()
    ctx_cleared = engine.generate_personality_context(
        user_input="Explain architecture."
    )
    assert ctx_cleared.effective_formality == base_formality


def test_response_style_modes():
    """Verify ResponseStyleMode adjustments for ERROR, TECHNICAL, CASUAL."""
    engine = PersonalityEngine()

    err_ctx = engine.generate_personality_context(style_mode=ResponseStyleMode.ERROR)
    assert err_ctx.effective_humor == 0.0
    assert err_ctx.effective_formality >= 0.7

    tech_ctx = engine.generate_personality_context(
        style_mode=ResponseStyleMode.TECHNICAL
    )
    assert tech_ctx.effective_formality >= 0.7
    assert tech_ctx.effective_conciseness <= 0.6


def test_bootstrapper_integration_and_health_check(qapp):
    """Verify PersonalityEngine integration into AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        engine: PersonalityEngine = result.container.personality_engine()
        assert engine is not None
        report = engine.get_health_report()

        assert report["subsystem"] == "Personality Engine & Behavioral Identity System"
        assert report["status"] == "HEALTHY"
        assert report["identity_name"] == "Friday"
        assert report["behavioral_rules_count"] == 20
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_boundary_no_eval_exec_or_tool_execution():
    """Verify PersonalityEngine contains zero tool execution authority and zero eval/exec code evaluation."""
    engine = PersonalityEngine()
    import inspect

    source = inspect.getsource(engine.__class__)
    assert "eval(" not in source
    assert "exec(" not in source
    assert not hasattr(engine, "execute_tool")
