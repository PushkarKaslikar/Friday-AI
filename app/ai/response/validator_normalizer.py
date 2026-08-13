"""Response validator and text normalizer for TTS and display formatting.

Phase 4.5 - Dynamic Response Generation Engine
"""

import re

from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class ResponseValidatorNormalizer:
    """Validates raw LLM response text, sanitizes secrets, and formats clean text/spoken outputs."""

    def validate_raw_response(self, text: str) -> tuple[bool, str | None]:
        """Validate raw response text against leakage, empty content, or malformed artifacts."""
        if not text or not text.strip():
            return False, "Response text is empty"

        clean = text.strip()

        # Check for system prompt leakage
        if (
            "### SYSTEM INSTRUCTIONS" in clean
            or "### FACTUAL GROUNDING DIRECTIVES" in clean
        ):
            return False, "Response leaked system prompt instructions"

        # Check for unmasked credential patterns
        if re.search(
            r"\b(api_key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?",
            clean,
            re.IGNORECASE,
        ):
            return False, "Response contains exposed credential pattern"

        return True, None

    def normalize(self, text: str) -> tuple[str, str]:
        """Normalize raw text into display response_text and TTS-friendly spoken_text."""
        if not text:
            return "", ""

        clean = text.strip()

        # 1. Strip markdown code fences if wrapped
        if clean.startswith("```json"):
            clean = clean.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif clean.startswith("```"):
            clean = clean.split("```", 1)[-1].split("```", 1)[0].strip()

        # 2. Strip JSON wrappers like {"response": "..."}
        if clean.startswith(('{"response":', '{"content":')):
            try:
                import json

                data = json.loads(clean)
                clean = data.get("response") or data.get("content") or clean
            except json.JSONDecodeError:
                pass

        # 3. Strip duplicate prefixes ("Friday: Friday:")
        clean = re.sub(r"^(Friday\s*:\s*)+", "", clean, flags=re.IGNORECASE).strip()

        # 4. Mask sensitive credentials
        clean = SensitiveDataSanitizer.sanitize_text(clean)

        # 5. Format spoken text for TTS (remove raw code paths, URLs, markdown formatting)
        spoken = clean
        spoken = re.sub(r"```[\s\S]*?```", "code block", spoken)
        spoken = re.sub(r"`([^`]+)`", r"\1", spoken)
        spoken = re.sub(r"https?://\S+", "link", spoken)
        spoken = re.sub(r"[#*_\-\\`]", "", spoken)

        return clean, spoken.strip()
