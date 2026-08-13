"""Response strategy selector for tone, verbosity, and mode adaptation.

Phase 4.5 - Dynamic Response Generation Engine
"""

from typing import Any

from app.ai.personality.models import EmotionalSignal
from app.ai.response.models import (
    ResponseGenerationMode,
    ResponseGenerationRequest,
    ResponseStatus,
)


class ResponseStrategySelector:
    """Selects target style parameters and prompt constraints based on mode and status."""

    def select_strategy(
        self, request: ResponseGenerationRequest, factual_status: ResponseStatus
    ) -> dict[str, Any]:
        """Determine target response style constraints."""
        mode = request.response_mode
        emot = (
            request.personality_context.emotional_signal
            if request.personality_context
            else EmotionalSignal.NEUTRAL
        )

        strategy = {
            "mode": mode.value,
            "target_verbosity": "CONCISE",
            "include_next_step": False,
            "ask_clarification": False,
            "style_instruction": "Provide a natural, clear, and direct response.",
        }

        # Status based overrides
        if factual_status == ResponseStatus.FAILED:
            strategy["mode"] = ResponseGenerationMode.ERROR.value
            strategy["include_next_step"] = True
            strategy["style_instruction"] = (
                "Clearly state that the action failed and explain why simply."
            )
        elif factual_status == ResponseStatus.PARTIAL_SUCCESS:
            strategy["mode"] = ResponseGenerationMode.WARNING.value
            strategy["style_instruction"] = (
                "State what succeeded and what failed clearly."
            )
        elif factual_status == ResponseStatus.DENIED:
            strategy["mode"] = ResponseGenerationMode.WARNING.value
            strategy["style_instruction"] = (
                "State that permission was denied for the operation."
            )

        # Mode based overrides
        if mode == ResponseGenerationMode.CLARIFICATION:
            strategy["ask_clarification"] = True
            strategy["style_instruction"] = (
                "Ask a single, clear clarification question."
            )
        elif mode == ResponseGenerationMode.TECHNICAL:
            strategy["target_verbosity"] = "DETAILED"
            strategy["style_instruction"] = "Provide clear technical details and steps."

        # Emotion based overrides
        if emot == EmotionalSignal.FRUSTRATED:
            strategy["target_verbosity"] = "CONCISE"
            strategy[
                "style_instruction"
            ] += " Be calm, empathetic, and focus strictly on solving the issue."

        return strategy
