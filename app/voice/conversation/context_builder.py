"""Prioritized Context Builder & Sensitive Data Sanitizer for Phase 3.8 & Phase 4.7.

Phase 3.8 & Phase 4.7 - Conversational Continuity & Short-Term Memory
"""

from typing import Any

from app.tools.execution.result_normalizer import SensitiveDataSanitizer
from app.voice.conversation.manager_models import (
    ContextSnapshot,
    ConversationalStateCategory,
    ConversationManagerConfiguration,
    ConversationTurn,
    PendingRequest,
    TrackedEntity,
)


class ContextBuilder:
    """Constructs prioritized, sanitized ContextSnapshots within context bounds."""

    def __init__(self, config: ConversationManagerConfiguration | None = None) -> None:
        self.config = config or ConversationManagerConfiguration()

    def build_snapshot(
        self,
        session_id: str,
        version: int,
        turns: list[ConversationTurn],
        entities: list[TrackedEntity],
        recent_commands: list[dict[str, Any]],
        recent_results: list[dict[str, Any]],
        current_topic: str = "GENERAL",
        pending_request: PendingRequest | None = None,
        conversational_state: ConversationalStateCategory = ConversationalStateCategory.NEW_REQUEST,
    ) -> ContextSnapshot:
        """Assemble structured, sanitized ContextSnapshot."""
        # 1. Sanitize sensitive information in commands, results, and metadata
        sanitized_commands = SensitiveDataSanitizer.sanitize(recent_commands[-5:])
        sanitized_results = SensitiveDataSanitizer.sanitize(recent_results[-5:])

        # Truncate large tool result payloads
        for res in sanitized_results:
            if isinstance(res, dict) and "result" in res:
                res_str = str(res["result"])
                if len(res_str) > self.config.max_tool_result_chars:
                    res["result"] = (
                        res_str[: self.config.max_tool_result_chars] + "...[TRUNCATED]"
                    )

        # 2. Priority-based turn eviction (retains newest turns up to max_turns)
        bounded_turns = turns[-self.config.max_turns :] if turns else []
        turn_dicts = [
            {
                "turn_number": t.turn_number,
                "speaker": t.speaker.value,
                "text": SensitiveDataSanitizer.sanitize_text(t.text),
                "conversational_state": getattr(
                    t, "conversational_state", ConversationalStateCategory.NEW_REQUEST
                ).value,
                "timestamp": t.timestamp,
            }
            for t in bounded_turns
        ]

        # 3. Format active entities
        bounded_entities = sorted(
            entities, key=lambda e: (e.turn_number, e.last_seen), reverse=True
        )[: self.config.max_entities]
        entity_dicts = [
            {
                "name": e.name,
                "category": e.category.value,
                "identifier": e.identifier,
                "turn_number": e.turn_number,
            }
            for e in bounded_entities
        ]

        # 4. Extract last user request and assistant response
        last_user = ""
        last_assistant = ""
        for t in reversed(bounded_turns):
            if not last_user and t.speaker.value == "USER":
                last_user = t.text
            elif not last_assistant and t.speaker.value == "ASSISTANT":
                last_assistant = t.text
            if last_user and last_assistant:
                break

        # 5. Enforce total character budget on context snapshot
        turn_dicts = self._enforce_character_budget(
            turn_dicts, self.config.max_context_characters
        )

        pending_dict = None
        if pending_request:
            pending_dict = {
                "pending_id": pending_request.pending_id,
                "original_text": pending_request.original_text,
                "original_intent": pending_request.original_intent,
                "missing_fields": pending_request.missing_fields,
                "clarification_prompt": pending_request.clarification_prompt,
                "expected_entity_type": pending_request.expected_entity_type,
                "candidate_options": pending_request.candidate_options,
            }

        return ContextSnapshot(
            session_id=session_id,
            version=version,
            recent_turns=turn_dicts,
            active_entities=entity_dicts,
            recent_commands=sanitized_commands,
            recent_results=sanitized_results,
            current_topic=current_topic,
            last_user_request=last_user,
            last_assistant_response=last_assistant,
            pending_request=pending_dict,
            conversational_state=conversational_state,
        )

    def _enforce_character_budget(
        self,
        turn_dicts: list[dict[str, Any]],
        max_chars: int,
    ) -> list[dict[str, Any]]:
        """Evict oldest turns if cumulative character count exceeds max_chars."""
        total_chars = sum(len(str(t.get("text", ""))) for t in turn_dicts)
        while turn_dicts and total_chars > max_chars:
            evicted = turn_dicts.pop(0)
            total_chars -= len(str(evicted.get("text", "")))

        return turn_dicts
