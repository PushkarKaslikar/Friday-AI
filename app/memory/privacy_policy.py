"""Formal memory privacy policy abstraction centralizing privacy rules.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from app.memory.privacy_models import (
    MemoryPrivacyConfig,
    MemoryPrivacyDecision,
    PrivacyMode,
    PrivacyReasonCode,
    PrivacySensitivity,
)
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class IMemoryPrivacyPolicy(ABC):
    """Abstract interface for Memory Privacy Policy."""

    @abstractmethod
    def classify_sensitivity(
        self, subject: str, content: str, memory_type: str = ""
    ) -> PrivacySensitivity:
        """Classify privacy sensitivity level of a memory item."""

    @abstractmethod
    def evaluate_write(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        source: str = "USER_EXPLICIT",
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate whether a memory can be persisted."""

    @abstractmethod
    def evaluate_read(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
        is_explicit_request: bool = False,
    ) -> MemoryPrivacyDecision:
        """Evaluate whether a memory can be retrieved into AI context."""

    @abstractmethod
    def evaluate_index(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate whether a memory can be semantically indexed in FAISS."""

    @abstractmethod
    def evaluate_profile(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate whether a memory can appear in active UserProfile."""


class MemoryPrivacyPolicy(IMemoryPrivacyPolicy):
    """Centralized privacy policy governing memory persistence, retrieval, indexing, and profile visibility."""

    RESTRICTED_KEYWORDS: ClassVar[set[str]] = {
        "password",
        "passcode",
        "api_key",
        "apikey",
        "secret",
        "private_key",
        "token",
        "bearer",
        "cookie",
        "auth_header",
        "credentials",
        "sk-proj-",
        "ghp_",
        "access_token",
    }

    SENSITIVE_KEYWORDS: ClassVar[set[str]] = {
        "therapist",
        "medical",
        "diagnosis",
        "doctor",
        "ssn",
        "social_security",
        "salary",
        "bank_account",
        "credit_card",
        "passport",
    }

    def __init__(self, config: MemoryPrivacyConfig | None = None) -> None:
        self.config = config or MemoryPrivacyConfig()

    def classify_sensitivity(
        self, subject: str, content: str, memory_type: str = ""
    ) -> PrivacySensitivity:
        """Classify privacy sensitivity level."""
        combined = f"{subject} {content} {memory_type}".lower()

        # 1. RESTRICTED Secret Credentials Check
        if any(k in combined for k in self.RESTRICTED_KEYWORDS):
            return PrivacySensitivity.RESTRICTED

        if SensitiveDataSanitizer.contains_sensitive_data(combined):
            return PrivacySensitivity.RESTRICTED

        # 2. SENSITIVE Personal Data Check
        if any(k in combined for k in self.SENSITIVE_KEYWORDS):
            return PrivacySensitivity.SENSITIVE

        # 3. PERSONAL Information
        m_type_upper = memory_type.upper()
        if m_type_upper in ("PROJECT", "CONTACT", "WORKFLOW") or subject.startswith(
            "user_"
        ):
            return PrivacySensitivity.PERSONAL

        # 4. NORMAL Preferences
        return PrivacySensitivity.NORMAL

    def evaluate_write(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        source: str = "USER_EXPLICIT",
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate write eligibility before persistence."""
        mode = mode_override or self.config.mode

        if not self.config.enabled:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.POLICY_DISABLED,
                message="Memory persistence is disabled in settings",
            )

        if mode == PrivacyMode.NO_PERSISTENCE:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.POLICY_DISABLED,
                retrieval_allowed=False,
                index_allowed=False,
                profile_allowed=False,
                message="NO_PERSISTENCE privacy mode active: persistent memory creation blocked",
            )

        sensitivity = self.classify_sensitivity(subject, content, memory_type)

        # Restricted credentials must be rejected immediately
        if sensitivity == PrivacySensitivity.RESTRICTED:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.RESTRICTED_DATA,
                sensitivity=sensitivity,
                index_allowed=False,
                retrieval_allowed=False,
                profile_allowed=False,
                message="Cannot persist restricted authentication credentials or secrets",
            )

        # STRICT mode requirement for personal/sensitive data
        requires_conf = False
        if mode == PrivacyMode.STRICT and sensitivity in (
            PrivacySensitivity.PERSONAL,
            PrivacySensitivity.SENSITIVE,
        ):
            requires_conf = True

        return MemoryPrivacyDecision(
            decision=True,
            reason_code=PrivacyReasonCode.ALLOWED,
            requires_confirmation=requires_conf,
            sensitivity=sensitivity,
            retention=self.config.default_retention,
            index_allowed=self.config.allow_semantic_indexing
            and (sensitivity != PrivacySensitivity.RESTRICTED),
            retrieval_allowed=True,
            profile_allowed=True,
            message="Write allowed under privacy policy",
        )

    def evaluate_read(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
        is_explicit_request: bool = False,
    ) -> MemoryPrivacyDecision:
        """Evaluate read eligibility before LLM context packaging."""
        mode = mode_override or self.config.mode
        sens = sensitivity or self.classify_sensitivity(subject, content, memory_type)

        if sens == PrivacySensitivity.RESTRICTED:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.RESTRICTED_DATA,
                sensitivity=sens,
                retrieval_allowed=False,
                message="Restricted secrets are blocked from LLM retrieval context",
            )

        if (
            sens == PrivacySensitivity.SENSITIVE
            and mode == PrivacyMode.STRICT
            and not is_explicit_request
        ):
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.RETRIEVAL_BLOCKED,
                sensitivity=sens,
                retrieval_allowed=False,
                message="Sensitive memory retrieval requires explicit request in STRICT mode",
            )

        return MemoryPrivacyDecision(
            decision=True,
            reason_code=PrivacyReasonCode.ALLOWED,
            sensitivity=sens,
            retrieval_allowed=True,
            message="Read allowed under privacy policy",
        )

    def evaluate_index(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate semantic vector indexing eligibility."""
        if not self.config.allow_semantic_indexing:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.INDEXING_BLOCKED,
                index_allowed=False,
                message="Semantic indexing disabled in privacy settings",
            )

        sens = sensitivity or self.classify_sensitivity(subject, content, memory_type)

        if sens == PrivacySensitivity.RESTRICTED:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.RESTRICTED_DATA,
                sensitivity=sens,
                index_allowed=False,
                message="Restricted credentials cannot be indexed in FAISS vector store",
            )

        return MemoryPrivacyDecision(
            decision=True,
            reason_code=PrivacyReasonCode.ALLOWED,
            sensitivity=sens,
            index_allowed=True,
            message="Vector indexing allowed under privacy policy",
        )

    def evaluate_profile(
        self,
        subject: str,
        content: str,
        memory_type: str = "",
        sensitivity: PrivacySensitivity | None = None,
        mode_override: PrivacyMode | None = None,
    ) -> MemoryPrivacyDecision:
        """Evaluate profile visibility eligibility."""
        sens = sensitivity or self.classify_sensitivity(subject, content, memory_type)

        if sens == PrivacySensitivity.RESTRICTED:
            return MemoryPrivacyDecision(
                decision=False,
                reason_code=PrivacyReasonCode.RESTRICTED_DATA,
                sensitivity=sens,
                profile_allowed=False,
                message="Restricted credentials excluded from UserProfile",
            )

        return MemoryPrivacyDecision(
            decision=True,
            reason_code=PrivacyReasonCode.ALLOWED,
            sensitivity=sens,
            profile_allowed=True,
            message="Profile inclusion allowed under privacy policy",
        )
