"""Central Dynamic Response Generation Engine implementation.

Phase 4.5 - Dynamic Response Generation Engine
"""

import threading
import time
from collections.abc import Iterator
from typing import Any

from app.ai.gateway.model_manager import LLMModelManager
from app.ai.models.models import AIRequest, ChatMessage, MessageRole
from app.ai.response.context_builder import ResponseContextBuilder
from app.ai.response.events import (
    ResponseGenerationCompleted,
    ResponseGenerationFailed,
    ResponseGenerationStarted,
)
from app.ai.response.generator_interface import IResponseGenerator
from app.ai.response.metrics import ResponseGenerationMetrics
from app.ai.response.models import (
    ResponseGenerationMode,
    ResponseGenerationRequest,
    ResponseMetadata,
    ResponseResult,
    ResponseStatus,
)
from app.ai.response.strategy_selector import ResponseStrategySelector
from app.ai.response.validator_normalizer import ResponseValidatorNormalizer
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus


class ResponseGenerator(BaseService, IResponseGenerator):
    """Central Response Generator converting workflow results and personality context into validated, factually grounded responses with fallback protection."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        llm_manager: LLMModelManager | None = None,
        context_builder: ResponseContextBuilder | None = None,
        strategy_selector: ResponseStrategySelector | None = None,
        validator_normalizer: ResponseValidatorNormalizer | None = None,
        metrics: ResponseGenerationMetrics | None = None,
    ) -> None:
        super().__init__(name="ResponseGenerator", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.llm_manager = llm_manager or LLMModelManager(
            config_manager=self.config_manager, event_bus=self.event_bus
        )
        self.context_builder = context_builder or ResponseContextBuilder()
        self.strategy_selector = strategy_selector or ResponseStrategySelector()
        self.validator_normalizer = (
            validator_normalizer or ResponseValidatorNormalizer()
        )
        self.metrics = metrics or ResponseGenerationMetrics()

        self._lock = threading.Lock()
        self._last_error: str | None = None

    def _do_initialize(self) -> None:
        """Initialize engine resources."""
        logger.info("ResponseGenerator initialized.")

    def _do_start(self) -> None:
        """Start engine service."""
        logger.info("ResponseGenerator started.")

    def _do_stop(self) -> None:
        """Stop engine service."""
        logger.info("ResponseGenerator stopped.")

    def generate_response(self, request: ResponseGenerationRequest) -> ResponseResult:
        """Execute full response generation turn with validation and fallback."""
        t_start = time.time()
        req_id = request.request_id

        self.event_bus.publish(
            ResponseGenerationStarted(
                request_id=req_id,
                response_mode=request.response_mode.value,
                user_input=request.user_input,
            )
        )

        # 1. Fact grounding status determination
        factual_status = self.context_builder.determine_factual_status(
            request.tool_results
        )

        # 2. Select strategy
        strategy = self.strategy_selector.select_strategy(request, factual_status)

        # 3. Assemble prompt context
        prompt_text = self.context_builder.build_prompt_context(request)

        # Build AIRequest for local LLM
        ai_req = AIRequest(
            request_id=f"{req_id}-resp",
            prompt=prompt_text,
            messages=[
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=strategy["style_instruction"],
                ),
                ChatMessage(role=MessageRole.USER, content=request.user_input),
            ],
            temperature=0.3,
            max_tokens=request.max_response_chars // 2,
        )

        # 4. LLM Generation & Fallback Guardrail
        try:
            ai_resp = self.llm_manager.generate(ai_req)
            raw_text = ai_resp.text.strip()

            # 5. Response Validation
            is_valid, val_error = self.validator_normalizer.validate_raw_response(
                raw_text
            )

            if not is_valid:
                logger.warning(
                    f"ResponseGenerator: Validation failed for request '{req_id}': {val_error}"
                )
                self.metrics.record_validation_failure()
                return self.format_fallback_response(
                    request, f"Validation failure: {val_error}"
                )

            # 6. Response Normalization & TTS formatting
            display_text, spoken_text = self.validator_normalizer.normalize(raw_text)

            duration_ms = (time.time() - t_start) * 1000.0

            res = ResponseResult(
                request_id=req_id,
                response_text=display_text,
                spoken_text=spoken_text,
                status=factual_status,
                response_mode=request.response_mode,
                metadata=ResponseMetadata(
                    generation_duration_ms=round(duration_ms, 2),
                    prompt_chars=len(prompt_text),
                    response_chars=len(display_text),
                    fallback_used=False,
                    model_name=ai_resp.model_name,
                    provider_type=ai_resp.provider_type,
                ),
                session_id=request.session_id,
                turn_id=request.turn_id,
            )

            self.metrics.record_generation(
                duration_ms=duration_ms,
                response_len=len(display_text),
                status=factual_status.value,
                mode=request.response_mode.value,
                fallback_used=False,
            )

            self.event_bus.publish(
                ResponseGenerationCompleted(
                    request_id=req_id,
                    status=factual_status.value,
                    duration_ms=duration_ms,
                    response_length=len(display_text),
                    fallback_used=False,
                )
            )

            return res

        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.time() - t_start) * 1000.0
            logger.error(
                f"ResponseGenerator: Generation exception for '{req_id}': {exc}"
            )
            return self.format_fallback_response(request, str(exc))

    def stream_response(self, request: ResponseGenerationRequest) -> Iterator[str]:
        """Stream generated response text tokens iteratively."""
        prompt_text = self.context_builder.build_prompt_context(request)
        ai_req = AIRequest(
            request_id=f"{request.request_id}-stream",
            prompt=prompt_text,
            temperature=0.3,
        )

        yield from self.llm_manager.generate_stream(ai_req)

    def format_fallback_response(
        self, request: ResponseGenerationRequest, error_reason: str
    ) -> ResponseResult:
        """Generate deterministic factual fallback response when LLM fails or times out."""
        factual_status = self.context_builder.determine_factual_status(
            request.tool_results
        )

        if factual_status == ResponseStatus.SUCCESS and request.tool_results:
            fallback_text = "Done. Action completed successfully."
        elif factual_status == ResponseStatus.FAILED:
            fallback_text = "I couldn't complete that action."
        elif factual_status == ResponseStatus.DENIED:
            fallback_text = "Authorization was denied for that action."
        elif factual_status == ResponseStatus.PARTIAL_SUCCESS:
            fallback_text = "The task completed partially, but one step failed."
        elif factual_status == ResponseStatus.CANCELLED:
            fallback_text = "The action was cancelled."
        else:
            fallback_text = "I don't have enough information to process that right now."

        display_text, spoken_text = self.validator_normalizer.normalize(fallback_text)

        res = ResponseResult(
            request_id=request.request_id,
            response_text=display_text,
            spoken_text=spoken_text,
            status=ResponseStatus.FALLBACK_USED,
            response_mode=ResponseGenerationMode.NORMAL,
            metadata=ResponseMetadata(
                fallback_used=True,
                response_chars=len(display_text),
            ),
            session_id=request.session_id,
            turn_id=request.turn_id,
        )

        self.metrics.record_generation(
            duration_ms=0.0,
            response_len=len(display_text),
            status=ResponseStatus.FALLBACK_USED.value,
            mode=request.response_mode.value,
            fallback_used=True,
        )

        self.event_bus.publish(
            ResponseGenerationFailed(
                request_id=request.request_id,
                error_message=error_reason,
                fallback_used=True,
            )
        )

        return res

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        return {
            "status": "HEALTHY" if not self._last_error else "DEGRADED",
            "subsystem": "Dynamic Response Generation Engine",
            "enabled": True,
            "max_response_chars": 2000,
            "streaming_enabled": True,
            "llm_provider_ready": True,
            "last_error": self._last_error,
            "metrics": self.metrics.get_metrics_snapshot(),
        }

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
