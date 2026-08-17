"""Deterministic retrieval trigger policy evaluating whether long-term memory retrieval is required.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import re
from typing import TYPE_CHECKING

from loguru import logger

from app.memory.retrieval_models import MemoryRetrievalRequest, RetrievalMode

if TYPE_CHECKING:
    from app.memory.retrieval_models import MemoryRetrievalConfig


# Explicit memory question patterns
EXPLICIT_MEMORY_PATTERNS = [
    r"\bwhat\s+(do\s+you|did\s+you)\s+remember\b",
    r"\bdo\s+you\s+remember\b",
    r"\bwhat\s+(is|are)\s+my\s+preferred\b",
    r"\bwhat\s+(editor|browser|theme|language|project)\s+do\s+i\s+(prefer|use|like)\b",
    r"\bmy\s+(saved|stored|known)\s+(preference|memory|profile)\b",
    r"\bwhat\s+(is|was)\s+my\s+usual\b",
    r"\bdo\s+you\s+know\s+my\b",
]

# Personal reference triggers
PERSONAL_REFERENCE_PATTERNS = [
    r"\bmy\s+usual\b",
    r"\bmy\s+preferred\b",
    r"\bnormally\s+use\b",
    r"\bmy\s+default\b",
    r"\bmy\s+favorite\b",
    r"\bmy\s+normal\b",
    r"\bmy\s+workflow\b",
    r"\bmy\s+project\b",
    r"\bmy\s+contact\b",
]

# Continuation triggers
CONTINUATION_PATTERNS = [
    r"\bcontinue\s+(working|the|our|on)\b",
    r"\bwhere\s+we\s+left\s+off\b",
    r"\bthe\s+project\s+we\s+discussed\b",
    r"\bpick\s+up\s+where\b",
]

# Action phrases that usually skip persistent memory search unless personal reference is present
SKIP_ACTION_PATTERNS = [
    r"^(hi|hello|hey|good\s+morning|good\s+evening|goodnight|thanks|thank\s+you)[\s!.]*$",
    r"^\d+\s*[\+\-\*\/]\s*\d+$",  # Math e.g. 2 + 2
    r"^set\s+volume\s+to\b",
    r"^mute\b",
    r"^unmute\b",
    r"^pause\b",
    r"^stop\b",
    r"^exit\b",
    r"^open\s+[a-z0-9_\-.]+$",  # Direct open command e.g. "open chrome"
]


class MemoryRetrievalPolicy:
    """Lightweight, deterministic policy deciding if long-term memory retrieval should execute."""

    def __init__(self, config: "MemoryRetrievalConfig | None" = None) -> None:
        self.config = config

    def should_retrieve(
        self, request: MemoryRetrievalRequest
    ) -> tuple[bool, RetrievalMode, str]:
        """Evaluate if memory retrieval should be triggered for a request.

        Returns:
            Tuple of (should_retrieve_bool, retrieval_mode, decision_reason)
        """
        if request.mode == RetrievalMode.NONE:
            return False, RetrievalMode.NONE, "Mode explicitly set to NONE"

        if request.mode == RetrievalMode.EXPLICIT:
            return True, RetrievalMode.EXPLICIT, "Mode explicitly set to EXPLICIT"

        text = request.user_text.strip().lower() if request.user_text else ""
        if not text:
            return False, RetrievalMode.NONE, "Empty user text"

        # Check explicit memory questions
        for pat in EXPLICIT_MEMORY_PATTERNS:
            if re.search(pat, text):
                logger.debug(
                    f"MemoryRetrievalPolicy: Triggered EXPLICIT pattern match '{pat}'."
                )
                return (
                    True,
                    RetrievalMode.EXPLICIT,
                    f"Matched explicit memory pattern: '{pat}'",
                )

        # Check personal reference requests
        for pat in PERSONAL_REFERENCE_PATTERNS:
            if re.search(pat, text):
                logger.debug(
                    f"MemoryRetrievalPolicy: Triggered PROFILE_FIRST pattern match '{pat}'."
                )
                return (
                    True,
                    RetrievalMode.PROFILE_FIRST,
                    f"Matched personal reference pattern: '{pat}'",
                )

        # Check continuation requests
        for pat in CONTINUATION_PATTERNS:
            if re.search(pat, text):
                logger.debug(
                    f"MemoryRetrievalPolicy: Triggered SESSION_FIRST pattern match '{pat}'."
                )
                return (
                    True,
                    RetrievalMode.SESSION_FIRST,
                    f"Matched continuation pattern: '{pat}'",
                )

        # Check skip actions
        for pat in SKIP_ACTION_PATTERNS:
            if re.search(pat, text):
                return (
                    False,
                    RetrievalMode.NONE,
                    f"Matched skip action pattern: '{pat}'",
                )

        # If user text contains possessive 'my' or 'our' and auto_trigger is enabled
        if ("my " in text or "our " in text) and (
            not self.config or self.config.auto_trigger
        ):
            return (
                True,
                RetrievalMode.AUTO,
                "Contains possessive pronoun reference ('my' / 'our')",
            )

        # Default fallback: skip retrieval for normal turn unless explicitly requested
        return False, RetrievalMode.NONE, "No retrieval triggers matched"
