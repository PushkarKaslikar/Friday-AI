"""Deterministic reference resolution engine for short-term conversational context.

Phase 3.8 & Phase 4.7 - Conversational Continuity & Short-Term Memory
"""

import re

from app.voice.conversation.manager_models import (
    EntityCategory,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    TrackedEntity,
)

PRONOUN_TRIGGERS: set[str] = {
    "it",
    "this",
    "that",
    "its",
    "them",
    "there",
    "here",
    "the previous one",
    "that project",
    "this project",
    "that one",
}
APP_TRIGGERS: set[str] = {"the app", "the application", "the program", "the app window"}
FILE_TRIGGERS: set[str] = {
    "the file",
    "the document",
    "the text file",
    "the article",
    "the readme",
    "the pdf",
    "the first pdf",
}
FOLDER_TRIGGERS: set[str] = {"the folder", "the directory"}
WEBSITE_TRIGGERS: set[str] = {
    "the website",
    "the site",
    "the page",
    "the tab",
    "the browser",
}
RESULT_FIRST_TRIGGERS: set[str] = {
    "the first result",
    "the 1st result",
    "first result",
    "the first one",
    "the 1st one",
    "first one",
}
RESULT_SECOND_TRIGGERS: set[str] = {
    "the second result",
    "the 2nd result",
    "second result",
    "the second one",
    "the 2nd one",
    "second one",
}
RESULT_LAST_TRIGGERS: set[str] = {
    "the last result",
    "the previous result",
    "latest result",
}


class DeterministicReferenceResolver:
    """Deterministic reference resolution engine for conversational entities."""

    def resolve_reference(
        self,
        user_input: str,
        entities: list[TrackedEntity],
    ) -> ReferenceResolutionResult:
        """Attempt to resolve entity reference in user input against active entity list."""
        clean_text = user_input.strip().lower()
        if not clean_text or not entities:
            return ReferenceResolutionResult(
                status=(
                    ReferenceResolutionStatus.NOT_APPLICABLE
                    if not clean_text
                    else ReferenceResolutionStatus.NOT_FOUND
                ),
                reference_text=user_input,
                reason=(
                    "No active entities in session context"
                    if clean_text
                    else "Empty user input"
                ),
            )

        # Detect trigger keywords
        ref_text = self._detect_reference_trigger(clean_text)
        if not ref_text:
            return ReferenceResolutionResult(
                status=ReferenceResolutionStatus.NOT_APPLICABLE,
                reference_text="",
                reason="No explicit reference pronoun or keyword detected",
            )

        # Filter candidate entities by category relevance
        candidates = self._filter_candidates(ref_text, entities)
        if not candidates:
            return ReferenceResolutionResult(
                status=ReferenceResolutionStatus.NOT_FOUND,
                reference_text=ref_text,
                reason=f"No matching entity candidates found for reference '{ref_text}'",
            )

        # Sort candidates by recency (highest turn_number first, then highest last_seen)
        sorted_candidates = sorted(
            candidates,
            key=lambda e: (e.turn_number, e.last_seen),
            reverse=True,
        )

        # Check for ambiguity: if top two candidates have identical turn_number and category
        if (
            len(sorted_candidates) > 1
            and sorted_candidates[0].turn_number == sorted_candidates[1].turn_number
            and sorted_candidates[0].category == sorted_candidates[1].category
            and sorted_candidates[0].name.lower() != sorted_candidates[1].name.lower()
        ):
            return ReferenceResolutionResult(
                status=ReferenceResolutionStatus.AMBIGUOUS,
                reference_text=ref_text,
                candidates=sorted_candidates[:3],
                confidence=0.5,
                reason=f"Multiple ambiguous {sorted_candidates[0].category.value} candidates in turn {sorted_candidates[0].turn_number}",
            )

        top_candidate = sorted_candidates[0]
        return ReferenceResolutionResult(
            status=ReferenceResolutionStatus.RESOLVED,
            reference_text=ref_text,
            resolved_entity=top_candidate,
            candidates=sorted_candidates[:3],
            confidence=1.0,
            reason=f"Resolved '{ref_text}' to entity '{top_candidate.name}' ({top_candidate.category.value}) from turn {top_candidate.turn_number}",
        )

    def _detect_reference_trigger(self, text: str) -> str:
        """Find matching reference trigger phrase in user input."""
        # Check specific phrase triggers first
        for trigger_set in (
            RESULT_FIRST_TRIGGERS,
            RESULT_SECOND_TRIGGERS,
            RESULT_LAST_TRIGGERS,
            APP_TRIGGERS,
            FILE_TRIGGERS,
            FOLDER_TRIGGERS,
            WEBSITE_TRIGGERS,
        ):
            for phrase in trigger_set:
                if phrase in text:
                    return phrase

        # Check pronoun word boundaries
        words = set(re.findall(r"\b\w+\b", text))
        for pronoun in PRONOUN_TRIGGERS:
            if pronoun in words:
                return pronoun

        return ""

    def _filter_candidates(
        self, ref_text: str, entities: list[TrackedEntity]
    ) -> list[TrackedEntity]:
        """Filter tracked entities matching category trigger."""
        if ref_text in APP_TRIGGERS:
            return [
                e
                for e in entities
                if e.category
                in (
                    EntityCategory.APPLICATION,
                    EntityCategory.WINDOW,
                    EntityCategory.PROCESS,
                )
            ]
        if ref_text in FILE_TRIGGERS:
            return [e for e in entities if e.category == EntityCategory.FILE]
        if ref_text in FOLDER_TRIGGERS:
            return [e for e in entities if e.category == EntityCategory.FOLDER]
        if ref_text in WEBSITE_TRIGGERS:
            return [
                e
                for e in entities
                if e.category in (EntityCategory.WEBSITE, EntityCategory.APPLICATION)
            ]
        if ref_text in RESULT_FIRST_TRIGGERS:
            # Sort by turn number asc or return first in list
            sorted_e = sorted(entities, key=lambda e: (e.turn_number, e.last_seen))
            return [sorted_e[0]] if sorted_e else []
        if ref_text in RESULT_SECOND_TRIGGERS:
            sorted_e = sorted(entities, key=lambda e: (e.turn_number, e.last_seen))
            return [sorted_e[1]] if len(sorted_e) > 1 else sorted_e
        if ref_text in RESULT_LAST_TRIGGERS:
            return sorted(entities, key=lambda e: e.last_seen, reverse=True)[:1]

        # General pronouns ("it", "this", "that") match any tracked entity
        return list(entities)
