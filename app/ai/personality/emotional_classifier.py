"""Lightweight deterministic conversational emotion signal classifier.

Phase 4.4 - Personality Engine & Behavioral Identity System
"""

import re
from typing import ClassVar

from app.ai.personality.models import EmotionalSignal


class EmotionalSignalClassifier:
    """Classifies user conversational input into lightweight tone signals."""

    FRUSTRATION_PATTERNS: ClassVar[list[str]] = [
        r"\b(frustrated|annoyed|angry|hate this|not working|broken|why is this taking|terrible|useless|stuck|slow)\b",
        r"\b(why doesn't this work|what is going on|ugh|damn|crap)\b",
        r"!{2,}",
    ]

    EXCITED_PATTERNS: ClassVar[list[str]] = [
        r"\b(finally|awesome|amazing|great|wonderful|fantastic|yay|woohoo|works!)\b",
        r"\b(it works|that worked|perfect)\b",
    ]

    URGENT_PATTERNS: ClassVar[list[str]] = [
        r"\b(urgent|asap|immediately|right now|quick|hurry|emergency)\b",
    ]

    CONFUSED_PATTERNS: ClassVar[list[str]] = [
        r"\b(confused|don't understand|what do you mean|huh\??|why did that happen|what is this)\b",
        r"\?{2,}",
    ]

    POSITIVE_PATTERNS: ClassVar[list[str]] = [
        r"\b(thanks|thank you|good job|nice|appreciate it|cool|great)\b",
    ]

    def classify(self, user_input: str) -> EmotionalSignal:
        """Classify user text into EmotionalSignal enum."""
        if not user_input or not user_input.strip():
            return EmotionalSignal.NEUTRAL

        text = user_input.lower().strip()

        for pat in self.FRUSTRATION_PATTERNS:
            if re.search(pat, text):
                return EmotionalSignal.FRUSTRATED

        for pat in self.URGENT_PATTERNS:
            if re.search(pat, text):
                return EmotionalSignal.URGENT

        for pat in self.EXCITED_PATTERNS:
            if re.search(pat, text):
                return EmotionalSignal.EXCITED

        for pat in self.CONFUSED_PATTERNS:
            if re.search(pat, text):
                return EmotionalSignal.CONFUSED

        for pat in self.POSITIVE_PATTERNS:
            if re.search(pat, text):
                return EmotionalSignal.POSITIVE

        return EmotionalSignal.NEUTRAL
