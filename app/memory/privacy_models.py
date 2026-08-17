"""Domain models and data structures for Phase 5.7 Memory Privacy & Governance.

Phase 5.7 - Memory Privacy, Security, Governance & User Control
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PrivacyMode(str, Enum):
    """Global operational privacy mode governing memory persistence and access."""

    NORMAL = "NORMAL"
    STRICT = "STRICT"
    NO_PERSISTENCE = "NO_PERSISTENCE"


class PrivacySensitivity(str, Enum):
    """Sensitivity level classification for stored memory content."""

    PUBLIC = "PUBLIC"
    NORMAL = "NORMAL"
    PERSONAL = "PERSONAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class RetentionCategory(str, Enum):
    """Retention lifecycle category for memory entries."""

    SESSION_ONLY = "SESSION_ONLY"
    TEMPORARY = "TEMPORARY"
    PERSISTENT = "PERSISTENT"
    UNTIL_DELETED = "UNTIL_DELETED"
    EXPIRING = "EXPIRING"


class PrivacyReasonCode(str, Enum):
    """Structured policy reason code for privacy decisions and audit events."""

    ALLOWED = "ALLOWED"
    EXPLICIT_REQUIRED = "EXPLICIT_REQUIRED"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    RESTRICTED_DATA = "RESTRICTED_DATA"
    USER_DENIED = "USER_DENIED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"
    POLICY_DISABLED = "POLICY_DISABLED"
    NOT_RELEVANT = "NOT_RELEVANT"
    INDEXING_BLOCKED = "INDEXING_BLOCKED"
    RETRIEVAL_BLOCKED = "RETRIEVAL_BLOCKED"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


class PrivacyStatus(str, Enum):
    """Health status of the Memory Privacy Governance Subsystem."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


@dataclass
class MemoryPrivacyDecision:
    """Outcome of a privacy governance evaluation."""

    decision: bool = True
    reason_code: PrivacyReasonCode = PrivacyReasonCode.ALLOWED
    requires_confirmation: bool = False
    sensitivity: PrivacySensitivity = PrivacySensitivity.NORMAL
    retention: RetentionCategory = RetentionCategory.PERSISTENT
    index_allowed: bool = True
    retrieval_allowed: bool = True
    profile_allowed: bool = True
    message: str = "Operation permitted under privacy policy"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryPrivacyConfig:
    """Configuration options for Memory Privacy Subsystem."""

    enabled: bool = True
    mode: PrivacyMode = PrivacyMode.NORMAL
    allow_persistent_memory: bool = True
    require_confirmation_for_personal: bool = False
    allow_semantic_indexing: bool = True
    allow_sensitive_retrieval: bool = True
    default_retention: RetentionCategory = RetentionCategory.PERSISTENT
    auto_cleanup: bool = True
    audit_enabled: bool = True
