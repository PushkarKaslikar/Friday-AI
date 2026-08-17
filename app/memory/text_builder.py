"""Memory-to-Text representation builder for vector embeddings.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import hashlib
from typing import TYPE_CHECKING

from app.tools.execution.result_normalizer import SensitiveDataSanitizer

if TYPE_CHECKING:
    from app.memory.long_term_models import LongTermMemoryEntry


class MemoryEmbeddingTextBuilder:
    """Converts LongTermMemoryEntry objects into clean, bounded, sanitized semantic text."""

    def __init__(self, max_chars: int = 1000) -> None:
        self._max_chars = max_chars
        self._sanitizer = SensitiveDataSanitizer()

    def build_embedding_text(self, entry: "LongTermMemoryEntry") -> str:
        """Convert a persistent long-term memory entry into a semantic embedding string."""
        if not entry:
            return ""

        # Security Check: Sanitize sensitive credentials
        raw_content = entry.content or ""
        raw_subject = entry.subject or ""

        if self._sanitizer.contains_sensitive_data(
            raw_content
        ) or self._sanitizer.contains_sensitive_data(raw_subject):
            # Sanitize content before embedding
            raw_content = "[REDACTED SECRET]"

        mem_type = entry.memory_type or "GENERAL"
        meta = entry.metadata or {}

        # Format deterministic semantic text based on memory type
        if mem_type == "PREFERENCE":
            text = f"The user prefers {raw_content} for {raw_subject}."
        elif mem_type == "PROJECT":
            desc = meta.get("description", "")
            aliases = ", ".join(meta.get("aliases", []))
            alias_str = f" Aliases: {aliases}." if aliases else ""
            text = f"Project: {raw_subject}. Path: {raw_content}. {desc}{alias_str}".strip()
        elif mem_type == "CONTACT":
            rel = raw_content or "Contact"
            org = meta.get("organization", "")
            org_str = f" Organization: {org}." if org else ""
            notes = meta.get("notes", "")
            text = (
                f"Contact: {raw_subject}, relationship: {rel}.{org_str} {notes}".strip()
            )
        elif mem_type == "WORKFLOW":
            desc = meta.get("description", "")
            steps = meta.get("steps", [])
            steps_str = "; ".join(steps) if isinstance(steps, list) else raw_content
            text = f"Workflow: {raw_subject}. {desc} Steps: {steps_str}".strip()
        else:
            text = f"Memory ({mem_type}): {raw_subject} - {raw_content}".strip()

        # Enforce max character limit
        if len(text) > self._max_chars:
            text = text[: self._max_chars - 3] + "..."

        return text

    def compute_content_hash(self, text: str) -> str:
        """Compute SHA-256 hash of the sanitized embedding text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
