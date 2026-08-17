"""Semantic memory query builder normalizing user requests for vector search.

Phase 5.6 - Memory Retrieval & Relevant Context Engine
"""

import re

FILLER_WORDS = [
    r"\bhey\s+friday\b",
    r"\bfriday\b",
    r"\bcould\s+you\s+please\b",
    r"\bcan\s+you\s+please\b",
    r"\bplease\b",
    r"\bwould\s+you\s+mind\b",
    r"\btell\s+me\b",
    r"\bdo\s+you\s+know\b",
    r"\bwhat\s+is\b",
    r"\bwhat\s+are\b",
    r"\bwhich\b",
]


class MemoryQueryBuilder:
    """Normalizes conversational user text into clean semantic vector query strings."""

    def __init__(self, max_query_chars: int = 200) -> None:
        self.max_query_chars = max_query_chars

    def build_query(
        self,
        user_text: str,
        current_intent: str | None = None,
        current_entities: list[str] | None = None,
    ) -> str:
        """Construct a normalized semantic query string from user input and turn metadata."""
        if not user_text:
            return ""

        text = user_text.strip().lower()

        # Strip conversational fillers
        for filler in FILLER_WORDS:
            text = re.sub(filler, "", text, flags=re.IGNORECASE)

        # Normalize whitespace and punctuation
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        tokens = text.split()

        # Incorporate active entities if not already present
        if current_entities:
            for ent in current_entities:
                ent_clean = ent.strip().lower()
                if ent_clean and ent_clean not in tokens:
                    tokens.append(ent_clean)

        # Reconstruct normalized query text
        query_str = " ".join(tokens)
        if len(query_str) > self.max_query_chars:
            query_str = query_str[: self.max_query_chars].rstrip()

        return query_str
