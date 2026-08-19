"""Central Greeting Service & Orchestrator for Phase 3.9.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

import threading
import time
from typing import Any

from app.ai.personality.personality_engine import PersonalityEngine
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.conversation.conversation_manager import ConversationManager
from app.voice.conversation.events import ConversationActivated
from app.voice.greeting.diagnostics import GreetingDiagnostics
from app.voice.greeting.events import (
    GreetingGenerated,
    GreetingGenerationFailed,
    GreetingGenerationStarted,
    GreetingSkipped,
    GreetingSpoken,
)
from app.voice.greeting.greeting_context_builder import GreetingContextBuilder
from app.voice.greeting.greeting_provider_interface import IGreetingProvider
from app.voice.greeting.metrics import GreetingMetrics
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingConfiguration,
    GreetingContext,
    GreetingResponse,
    GreetingStyle,
)
from app.voice.greeting.template_provider import TemplateGreetingProvider
from app.voice.tts.tts_service import TTSService


class GreetingService(BaseService):
    """Central service managing context-aware greeting selection, fallbacks, and TTS dispatch."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        conversation_manager: ConversationManager | None = None,
        tts_service: TTSService | None = None,
        provider: IGreetingProvider | None = None,
        context_builder: GreetingContextBuilder | None = None,
        personality_engine: PersonalityEngine | None = None,
        metrics: GreetingMetrics | None = None,
        diagnostics: GreetingDiagnostics | None = None,
    ) -> None:
        super().__init__(name="GreetingService", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.conversation_manager = conversation_manager
        self.tts_service = tts_service
        self.provider = provider or TemplateGreetingProvider()
        self.context_builder = context_builder or GreetingContextBuilder(
            conversation_manager=self.conversation_manager
        )
        self.personality_engine = personality_engine or PersonalityEngine(
            config_manager=self.config_manager,
            event_bus=self.event_bus,
        )
        self.metrics = metrics or GreetingMetrics()
        self.diagnostics = diagnostics or GreetingDiagnostics(metrics=self.metrics)

        self._greeting_config: GreetingConfiguration = (
            self._load_greeting_configuration()
        )
        self._lock = threading.Lock()
        self._last_error: str | None = None

    @property
    def greeting_config(self) -> GreetingConfiguration:
        """Active configuration settings."""
        return self._greeting_config

    def _load_greeting_configuration(self) -> GreetingConfiguration:
        """Load greeting settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "greeting"):
                cfg = settings.greeting
                return GreetingConfiguration(
                    enabled=cfg.enabled,
                    max_recent_history=cfg.max_recent_history,
                    avoid_repetition=cfg.avoid_repetition,
                    default_style=(
                        GreetingStyle(cfg.default_style)
                        if hasattr(GreetingStyle, cfg.default_style)
                        else GreetingStyle.FRIDAY
                    ),
                    use_context=cfg.use_context,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"GreetingService: Failed to load settings, using defaults: {exc}"
            )

        return GreetingConfiguration()

    def _do_initialize(self) -> None:
        """Initialize parameters."""
        logger.info("GreetingService: Service initialized.")

    def _do_start(self) -> None:
        """Subscribe to EventBus lifecycle activation event."""
        self.event_bus.subscribe(ConversationActivated, self._on_conversation_activated)
        logger.info("GreetingService: Subscribed to ConversationActivated event.")

    def _do_stop(self) -> None:
        """Stop service."""
        logger.info("GreetingService: Service stopped.")

    def generate_greeting(
        self,
        session_id: str,
        activation_source: str = "WAKE_WORD",
    ) -> GreetingResponse:
        """Generate context-aware greeting response with safe fallback protection."""
        t_start = time.time()
        with self._lock:
            if not self._greeting_config.enabled:
                self.metrics.record_skipped()
                self.event_bus.publish(
                    GreetingSkipped(session_id=session_id, reason="greetings_disabled")
                )
                return GreetingResponse(
                    text="",
                    category=GreetingCategory.FALLBACK,
                    provider=self.provider.provider_name,
                    session_id=session_id,
                    should_speak=False,
                )

            self.event_bus.publish(
                GreetingGenerationStarted(
                    session_id=session_id, activation_source=activation_source
                )
            )

            try:
                ctx: GreetingContext = self.context_builder.build_context(
                    session_id=session_id, activation_source=activation_source
                )
                response = self.provider.generate_greeting(ctx)
                latency_ms = (time.time() - t_start) * 1000.0
                self.metrics.record_generation(latency_ms)

                self.event_bus.publish(
                    GreetingGenerated(
                        session_id=session_id,
                        text=response.text,
                        category=response.category.value,
                        provider=response.provider,
                    )
                )

                # Speak greeting via TTSService if configured and active
                if response.should_speak and self.tts_service and response.text:
                    try:
                        self.tts_service.speak(response.text)
                        self.metrics.record_spoken()
                        self.event_bus.publish(
                            GreetingSpoken(session_id=session_id, text=response.text)
                        )
                    except Exception as tts_exc:  # noqa: BLE001
                        logger.error(
                            f"GreetingService: Failed to dispatch TTS greeting: {tts_exc}"
                        )

                return response

            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                logger.error(
                    f"GreetingService: Exception during greeting generation, using fallback: {exc}"
                )
                self.metrics.record_failure(fallback_used=True)
                self.event_bus.publish(
                    GreetingGenerationFailed(
                        session_id=session_id,
                        error_message=str(exc),
                        fallback_used=True,
                    )
                )

                fallback_text = "How can I help?"
                if self.tts_service:
                    try:
                        self.tts_service.speak(fallback_text)
                    except Exception as fallback_exc:  # noqa: BLE001
                        logger.warning(
                            f"GreetingService: Failed to dispatch fallback TTS: {fallback_exc}"
                        )

                return GreetingResponse(
                    text=fallback_text,
                    category=GreetingCategory.FALLBACK,
                    provider="FallbackProvider",
                    session_id=session_id,
                    should_speak=True,
                )

    def generate_activation_greeting(
        self, session_id: str, activation_source: str = "WAKE_WORD"
    ) -> GreetingResponse:
        """Alias for generate_greeting for activation workflows."""
        return self.generate_greeting(session_id, activation_source)

    def _on_conversation_activated(self, evt: ConversationActivated) -> None:
        """EventBus callback handler for conversation activation events."""
        self.generate_greeting(evt.session_id, evt.activation_source)

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        with self._lock:
            recent_count = (
                len(self.provider.selector._recent_greetings)
                if hasattr(self.provider, "selector")
                else 0
            )

        return self.diagnostics.get_health_report(
            service_state="RUNNING" if self.is_running else "STOPPED",
            enabled=self._greeting_config.enabled,
            provider_name=self.provider.provider_name,
            context_aware=self._greeting_config.use_context,
            recent_greeting_count=recent_count,
            max_history=self._greeting_config.max_recent_history,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
