"""Authorization Provider interface and Development implementation for security validation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.models.command import CommandSource


class AuthorizationStatus(str, Enum):
    """Authorization evaluation decision status."""

    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class AuthorizationResult:
    """Authorization evaluation result model."""

    status: AuthorizationStatus = AuthorizationStatus.AUTHORIZED
    reason: str = "Execution authorized."
    missing_permissions: list[ToolPermission] = field(default_factory=list)

    @property
    def is_authorized(self) -> bool:
        return self.status == AuthorizationStatus.AUTHORIZED


class IAuthorizationProvider(ABC):
    """Abstract interface contract for tool execution authorization providers."""

    @abstractmethod
    def authorize_execution(
        self,
        metadata: ToolMetadata,
        source: CommandSource = CommandSource.USER,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AuthorizationResult:
        """Evaluate authorization policy for a tool request."""


class DevAuthorizationProvider(IAuthorizationProvider):
    """Configurable Authorization Provider for testing and development environments."""

    def __init__(
        self,
        mode: str = "DEFAULT",  # "DEFAULT", "ALLOW_ALL", "DENY_ALL", "REQUIRE_CONFIRMATION"
        granted_permissions: set[ToolPermission] | None = None,
    ) -> None:
        self.mode = mode
        self.granted_permissions: set[ToolPermission] = (
            granted_permissions
            if granted_permissions is not None
            else set(ToolPermission)
        )

    def authorize_execution(
        self,
        metadata: ToolMetadata,
        source: CommandSource = CommandSource.USER,
        granted_permissions: set[ToolPermission] | None = None,
    ) -> AuthorizationResult:
        """Evaluate authorization based on mode, risk level, required permissions, and user confirmation flag."""
        if self.mode == "ALLOW_ALL":
            return AuthorizationResult(
                status=AuthorizationStatus.AUTHORIZED,
                reason="Dev mode ALLOW_ALL active.",
            )

        if self.mode == "DENY_ALL":
            return AuthorizationResult(
                status=AuthorizationStatus.DENIED,
                reason="Dev mode DENY_ALL active.",
            )

        if self.mode == "REQUIRE_CONFIRMATION":
            return AuthorizationResult(
                status=AuthorizationStatus.CONFIRMATION_REQUIRED,
                reason="Dev mode REQUIRE_CONFIRMATION active.",
            )

        # Check explicit permission capabilities (Default Deny)
        effective_granted = (
            granted_permissions
            if granted_permissions is not None
            else self.granted_permissions
        )
        missing = [p for p in metadata.permissions if p not in effective_granted]
        if missing:
            return AuthorizationResult(
                status=AuthorizationStatus.DENIED,
                reason=f"Missing required permissions: {[p.value for p in missing]}",
                missing_permissions=missing,
            )

        # Check explicit tool metadata confirmation_required or HIGH/CRITICAL risk level
        if metadata.confirmation_required or metadata.risk_level in (
            ToolRiskLevel.HIGH,
            ToolRiskLevel.CRITICAL,
        ):
            return AuthorizationResult(
                status=AuthorizationStatus.CONFIRMATION_REQUIRED,
                reason=f"Tool requires explicit confirmation (Risk: {metadata.risk_level.value}).",
            )

        return AuthorizationResult(
            status=AuthorizationStatus.AUTHORIZED,
            reason="Tool permissions satisfied.",
        )
