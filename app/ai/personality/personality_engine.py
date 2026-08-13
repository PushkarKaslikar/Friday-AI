"""Central Personality Engine & Behavioral Identity System implementation.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

import threading
import time
from typing import Any

from app.ai.personality.behavioral_rules import BehavioralRulesEngine
from app.ai.personality.emotional_classifier import EmotionalSignalClassifier
from app.ai.personality.engine_interface import IPersonalityEngine
from app.ai.personality.events import (
    PersonalityContextGenerated,
    PersonalityModifierApplied,
)
from app.ai.personality.metrics import PersonalityMetrics
from app.ai.personality.models import (
    CommunicationStyle,
    EmotionalSignal,
    IdentityProfile,
    PersonalityContext,
    PersonalityModifier,
    PersonalityProfile,
    ResponseStyleMode,
    UserRelationship,
)
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus


class PersonalityEngine(BaseService, IPersonalityEngine):
    """Central engine managing personality profiles, emotion classification, dynamic modifiers, and compact model system prompt generation."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        classifier: EmotionalSignalClassifier | None = None,
        rules_engine: BehavioralRulesEngine | None = None,
        metrics: PersonalityMetrics | None = None,
    ) -> None:
        super().__init__(name="PersonalityEngine", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.classifier = classifier or EmotionalSignalClassifier()
        self.rules_engine = rules_engine or BehavioralRulesEngine()
        self.metrics = metrics or PersonalityMetrics()

        self._lock = threading.Lock()
        self._active_modifiers: list[PersonalityModifier] = []
        self._last_error: str | None = None
        self._base_profile = self._load_profile_from_settings()

    def get_personality_profile(self) -> PersonalityProfile:
        """Retrieve active base personality profile."""
        with self._lock:
            return self._base_profile

    def _load_profile_from_settings(self) -> PersonalityProfile:
        """Load base personality settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "friday") or hasattr(settings, "personality"):
                cfg = getattr(settings, "friday", None) or getattr(
                    settings, "personality", None
                )
                if cfg:
                    return PersonalityProfile(
                        identity=IdentityProfile(
                            name=getattr(cfg, "name", "Friday"),
                            role=getattr(cfg, "role", "Personal AI Assistant"),
                        ),
                        communication=CommunicationStyle(
                            formality=float(getattr(cfg, "formality", 0.5)),
                            humor=float(getattr(cfg, "humor", 0.25)),
                            emotional_responsiveness=float(
                                getattr(cfg, "emotional_responsiveness", 0.7)
                            ),
                            proactivity=float(getattr(cfg, "proactivity", 0.4)),
                            conciseness=float(getattr(cfg, "conciseness", 0.75)),
                        ),
                        relationship=UserRelationship(
                            preferred_name=getattr(cfg, "preferred_name", None),
                            address_style=getattr(cfg, "address_style", "natural"),
                        ),
                        behavioral_rules=self.rules_engine.get_all_rules(),
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"PersonalityEngine: Failed to load profile from config: {exc}"
            )

        return PersonalityProfile(behavioral_rules=self.rules_engine.get_all_rules())

    def _do_initialize(self) -> None:
        """Initialize engine resources."""
        logger.info("PersonalityEngine initialized.")

    def _do_start(self) -> None:
        """Start engine service."""
        logger.info("PersonalityEngine started.")

    def _do_stop(self) -> None:
        """Stop engine service."""
        logger.info("PersonalityEngine stopped.")

    def apply_temporary_modifier(self, modifier: PersonalityModifier) -> None:
        """Apply temporary personality modifier to active context stack."""
        with self._lock:
            self._active_modifiers.append(modifier)
            self.metrics.record_modifier_applied()
            self.event_bus.publish(
                PersonalityModifierApplied(
                    source=modifier.source,
                    reason=modifier.reason,
                )
            )

    def clear_modifiers(self) -> None:
        """Clear all temporary active modifiers."""
        with self._lock:
            self._active_modifiers.clear()

    def _get_active_modifiers_unlocked(self) -> list[PersonalityModifier]:
        """Filter out expired modifiers."""
        now = time.time()
        valid: list[PersonalityModifier] = []
        for m in self._active_modifiers:
            if now - m.timestamp < m.duration_seconds:
                valid.append(m)
        self._active_modifiers = valid
        return valid

    def generate_personality_context(
        self,
        user_input: str = "",
        style_mode: ResponseStyleMode = ResponseStyleMode.NORMAL,
        modifiers: list[PersonalityModifier] | None = None,
    ) -> PersonalityContext:
        """Generate effective model-facing PersonalityContext for a request."""
        t_start = time.time()

        # 1. Emotion classification
        emotional_signal = self.classifier.classify(user_input)

        with self._lock:
            base_comm = self._base_profile.communication
            identity = self._base_profile.identity

            # 2. Base values
            eff_formality = base_comm.formality
            eff_humor = base_comm.humor
            eff_emot = base_comm.emotional_responsiveness
            eff_pro = base_comm.proactivity
            eff_con = base_comm.conciseness

            # 3. Emotional signal adjustment
            if emotional_signal == EmotionalSignal.FRUSTRATED:
                eff_humor = 0.05
                eff_emot = 0.95
                eff_con = 0.85
                eff_formality = 0.6
            elif emotional_signal == EmotionalSignal.URGENT:
                eff_humor = 0.0
                eff_con = 0.95
                eff_formality = 0.7
            elif emotional_signal == EmotionalSignal.EXCITED:
                eff_humor = min(eff_humor + 0.15, 0.6)
                eff_emot = min(eff_emot + 0.15, 0.9)
            elif emotional_signal == EmotionalSignal.CONFUSED:
                eff_con = max(eff_con - 0.25, 0.3)
                eff_formality = max(eff_formality, 0.6)

            # 4. Response style mode adjustment
            if style_mode == ResponseStyleMode.ERROR:
                eff_humor = 0.0
                eff_formality = 0.75
                eff_con = 0.8
            elif style_mode == ResponseStyleMode.TECHNICAL:
                eff_formality = 0.8
                eff_humor = 0.1
                eff_con = 0.5
            elif style_mode == ResponseStyleMode.CASUAL:
                eff_formality = 0.3
                eff_humor = min(eff_humor + 0.1, 0.5)

            # 5. Apply active modifiers stack
            active_mods = self._get_active_modifiers_unlocked()
            if modifiers:
                active_mods = active_mods + modifiers

            for mod in active_mods:
                eff_formality += mod.formality_delta
                eff_humor += mod.humor_delta
                eff_emot += mod.emotional_responsiveness_delta
                eff_pro += mod.proactivity_delta
                eff_con += mod.conciseness_delta

            # 6. Clamp values to [0.0, 1.0]
            eff_formality = max(0.0, min(1.0, eff_formality))
            eff_humor = max(0.0, min(1.0, eff_humor))
            eff_emot = max(0.0, min(1.0, eff_emot))
            eff_pro = max(0.0, min(1.0, eff_pro))
            eff_con = max(0.0, min(1.0, eff_con))

            # Build context object
            ctx = PersonalityContext(
                identity_name=identity.name,
                role=identity.role,
                style_mode=style_mode,
                emotional_signal=emotional_signal,
                effective_formality=round(eff_formality, 2),
                effective_humor=round(eff_humor, 2),
                effective_emotional_responsiveness=round(eff_emot, 2),
                effective_proactivity=round(eff_pro, 2),
                effective_conciseness=round(eff_con, 2),
                system_prompt_snippet="",
            )

            # 7. Generate compact system prompt snippet
            snippet = self.build_model_system_prompt_snippet(ctx)
            ctx.system_prompt_snippet = snippet

            duration_ms = (time.time() - t_start) * 1000.0
            self.metrics.record_context_generation(
                duration_ms=duration_ms,
                snippet_len=len(snippet),
                emotional_signal=emotional_signal.value,
                style_mode=style_mode.value,
            )

            self.event_bus.publish(
                PersonalityContextGenerated(
                    identity_name=identity.name,
                    style_mode=style_mode.value,
                    emotional_signal=emotional_signal.value,
                    prompt_snippet_length=len(snippet),
                )
            )

            return ctx

    def build_model_system_prompt_snippet(self, context: PersonalityContext) -> str:
        """Format compact system prompt snippet for LLM inference instructions (< 150 tokens, ~400 chars)."""
        name = context.identity_name
        pref_name = self._base_profile.relationship.preferred_name

        lines = [
            f"You are {name}, the user's personal AI assistant.",
        ]

        if pref_name:
            lines.append(
                f"The user's preferred name is '{pref_name}'. Address them naturally."
            )

        if context.effective_conciseness >= 0.7:
            lines.append("Keep simple responses concise, direct, and actionable.")
        elif context.effective_conciseness <= 0.4:
            lines.append("Provide clear explanations and detailed steps.")

        if context.effective_humor > 0.3:
            lines.append("Use subtle, natural humor when appropriate.")
        else:
            lines.append("Maintain a direct, focused, and professional tone.")

        if context.emotional_signal == EmotionalSignal.FRUSTRATED:
            lines.append(
                "Respond empathetically to user frustration and focus on solving the issue."
            )

        lines.extend(
            [
                "Never claim an action succeeded unless execution results confirm it.",
                "Never fabricate facts or expose secret credentials.",
            ]
        )

        return "\n".join(lines)

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        with self._lock:
            identity = self._base_profile.identity
            comm = self._base_profile.communication
            active_mods_count = len(self._active_modifiers)
            rules_count = len(self._base_profile.behavioral_rules)

        return {
            "status": "HEALTHY" if not self._last_error else "DEGRADED",
            "subsystem": "Personality Engine & Behavioral Identity System",
            "enabled": True,
            "identity_name": identity.name,
            "formality": comm.formality,
            "humor": comm.humor,
            "active_modifiers_count": active_mods_count,
            "behavioral_rules_count": rules_count,
            "last_error": self._last_error,
            "metrics": self.metrics.get_metrics_snapshot(),
        }

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
