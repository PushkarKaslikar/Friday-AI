"""Intelligent AI Greeting Provider leveraging Local LLM and Personality Engine.

Phase 4.6 - Contextual Greetings & Intelligent Activation Responses
"""

import threading
import time
from typing import Any

from app.ai.gateway.model_manager import LLMModelManager
from app.ai.models.models import AIRequest, ChatMessage, MessageRole
from app.ai.personality.personality_engine import PersonalityEngine
from app.ai.response.validator_normalizer import ResponseValidatorNormalizer
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.events.event_bus import EventBus
from app.tools.execution.result_normalizer import SensitiveDataSanitizer
from app.voice.greeting.greeting_provider_interface import IGreetingProvider
from app.voice.greeting.metrics import GreetingMetrics
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingContext,
    GreetingResponse,
)
from app.voice.greeting.template_provider import TemplateGreetingProvider


class AIGreetingProvider(IGreetingProvider):
    """Contextual AI greeting provider synthesizing natural, personality-aware greetings via Local LLM with template fallback."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        llm_manager: LLMModelManager | None = None,
        personality_engine: PersonalityEngine | None = None,
        validator_normalizer: ResponseValidatorNormalizer | None = None,
        template_fallback_provider: TemplateGreetingProvider | None = None,
        metrics: GreetingMetrics | None = None,
    ) -> None:
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.llm_manager = llm_manager or LLMModelManager(
            config_manager=self.config_manager, event_bus=self.event_bus
        )
        self.personality_engine = personality_engine or PersonalityEngine(
            config_manager=self.config_manager, event_bus=self.event_bus
        )
        self.validator_normalizer = (
            validator_normalizer or ResponseValidatorNormalizer()
        )
        self.template_fallback_provider = (
            template_fallback_provider or TemplateGreetingProvider()
        )
        self.metrics = metrics or GreetingMetrics()

        self._lock = threading.Lock()

    @property
    def provider_name(self) -> str:
        """Return provider identifier name."""
        return "AIGreetingProvider"

    def generate_greeting(self, context: GreetingContext) -> GreetingResponse:
        """Generate intelligent context-aware greeting using local LLM with deterministic template fallback."""
        t_start = time.time()

        # 1. Check settings
        ai_enabled = True
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "greeting"):
                ai_enabled = getattr(settings.greeting, "ai_enabled", True)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"AIGreetingProvider: Settings check fallback: {exc}")

        if not ai_enabled:
            logger.info(
                "AIGreetingProvider: AI greetings disabled, using template fallback."
            )
            return self.template_fallback_provider.generate_greeting(context)

        # 2. Build personality context
        pers_ctx = self.personality_engine.generate_personality_context(
            user_input=context.last_user_interaction or "hello"
        )

        # 3. Assemble prompt context
        prompt_text = self._build_greeting_prompt(context, pers_ctx)

        ai_req = AIRequest(
            request_id=f"greet-{context.session_id}-{int(time.time())}",
            prompt=prompt_text,
            messages=[
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You are Friday. Generate ONLY a single concise greeting sentence (max 2 short sentences). Do NOT claim actions were performed. Do NOT fabricate completed tasks.",
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"Generate greeting for activation ({context.activation_source}).",
                ),
            ],
            temperature=0.4,
            max_tokens=64,
        )

        # 4. Execute LLM generation with fallback safety
        try:
            ai_resp = self.llm_manager.generate(ai_req)
            raw_text = ai_resp.text.strip()

            # 5. Validate & Normalize output
            is_valid, val_err = self.validator_normalizer.validate_raw_response(
                raw_text
            )
            if not is_valid or len(raw_text) > 150:
                logger.warning(
                    f"AIGreetingProvider: Invalid greeting response ('{raw_text}'): {val_err}. Falling back."
                )
                return self.template_fallback_provider.generate_greeting(context)

            clean_text, spoken_text = self.validator_normalizer.normalize(raw_text)
            clean_text = SensitiveDataSanitizer.sanitize_text(clean_text)
            spoken_text = SensitiveDataSanitizer.sanitize_text(spoken_text)

            duration_ms = (time.time() - t_start) * 1000.0

            category = (
                GreetingCategory.RETURNING
                if context.is_returning_session
                else GreetingCategory(context.time_of_day.value)
            )

            return GreetingResponse(
                text=clean_text,
                category=category,
                provider=self.provider_name,
                session_id=context.session_id,
                should_speak=True,
                metadata={
                    "spoken_text": spoken_text,
                    "generation_duration_ms": round(duration_ms, 2),
                    "ai_generated": True,
                    "model_name": ai_resp.model_name,
                },
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"AIGreetingProvider: Generation exception ({exc}). Falling back to template."
            )
            return self.template_fallback_provider.generate_greeting(context)

    def _build_greeting_prompt(self, context: GreetingContext, pers_ctx: Any) -> str:
        """Build structured model prompt context for greeting generation."""
        parts: list[str] = []

        if pers_ctx and hasattr(pers_ctx, "system_prompt_snippet"):
            parts.append(pers_ctx.system_prompt_snippet)

        parts.append("### ACTIVATION CONTEXT")
        parts.append(f"- Time of Day: {context.time_of_day.value}")
        parts.append(f"- Activation Source: {context.activation_source}")
        parts.append(
            f"- Session Status: {'RETURNING SESSION' if context.is_returning_session else 'NEW SESSION'}"
        )

        if (
            context.current_conversation_topic
            and context.current_conversation_topic != "GENERAL"
        ):
            parts.append(f"- Active Topic: {context.current_conversation_topic}")

        if context.last_user_interaction:
            clean_last = SensitiveDataSanitizer.sanitize_text(
                context.last_user_interaction[:150]
            )
            parts.append(f'- Previous Interaction: "{clean_last}"')

        parts.append("\nGenerate a natural 1-sentence greeting.")

        return "\n".join(parts)
