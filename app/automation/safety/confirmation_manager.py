"""Confirmation Manager handling structured user confirmation lifecycles and replay protection."""

import hashlib
import threading

from app.automation.safety.models import (
    AutomationConfirmationRequest,
    AutomationConfirmationStatus,
)
from app.logging import logger
from app.tools.base.risk import ToolRiskLevel


class AutomationConfirmationManager:
    """Manages pending user confirmation requests with short-lived expiration and fingerprint replay protection."""

    def __init__(self, default_expiration_ms: int = 30000) -> None:
        self._lock = threading.Lock()
        self.default_expiration_ms = default_expiration_ms
        self._pending_requests: dict[str, AutomationConfirmationRequest] = {}
        self._used_fingerprints: set[str] = set()

    def generate_fingerprint(
        self, workflow_id: str | None, action_summary: str, risk_level: ToolRiskLevel
    ) -> str:
        """Generate deterministic fingerprint hash for replay protection."""
        payload = f"{workflow_id or 'single'}:{action_summary}:{risk_level.value}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def create_request(
        self,
        reason: str,
        risk_level: ToolRiskLevel,
        action_summary: str,
        affected_resources: list[str] | None = None,
        workflow_id: str | None = None,
        tool_id: str | None = None,
        expiration_ms: int | None = None,
    ) -> AutomationConfirmationRequest:
        """Create a pending user confirmation request."""
        fingerprint = self.generate_fingerprint(workflow_id, action_summary, risk_level)
        exp_ms = expiration_ms or self.default_expiration_ms

        req = AutomationConfirmationRequest(
            workflow_id=workflow_id,
            tool_id=tool_id,
            reason=reason,
            risk_level=risk_level,
            action_summary=action_summary,
            affected_resources=affected_resources or [],
            expiration_ms=exp_ms,
            fingerprint=fingerprint,
            status=AutomationConfirmationStatus.PENDING,
        )

        with self._lock:
            self._pending_requests[req.confirmation_id] = req
            logger.info(
                f"AutomationConfirmationManager: Created confirmation request '{req.confirmation_id}' for risk {risk_level.value}."
            )
            return req

    def resolve_confirmation(
        self,
        confirmation_id: str,
        confirmed: bool,
        trusted_source: bool = True,
    ) -> AutomationConfirmationStatus:
        """Resolve a pending confirmation request via explicit trusted user interaction."""
        with self._lock:
            req = self._pending_requests.get(confirmation_id)
            if not req:
                return AutomationConfirmationStatus.CANCELLED

            if req.status != AutomationConfirmationStatus.PENDING:
                return req.status

            if not trusted_source:
                logger.warning(
                    f"Confirmation resolution for '{confirmation_id}' rejected: Untrusted source."
                )
                req.status = AutomationConfirmationStatus.DENIED
                return req.status

            if confirmed:
                if req.fingerprint in self._used_fingerprints:
                    logger.warning(
                        f"Replay attack protection: Fingerprint '{req.fingerprint}' already used!"
                    )
                    req.status = AutomationConfirmationStatus.DENIED
                    return req.status

                self._used_fingerprints.add(req.fingerprint)
                req.status = AutomationConfirmationStatus.CONFIRMED
                logger.info(
                    f"Confirmation request '{confirmation_id}' CONFIRMED by user."
                )
            else:
                req.status = AutomationConfirmationStatus.DENIED
                logger.info(f"Confirmation request '{confirmation_id}' DENIED by user.")

            return req.status

    def get_request(self, confirmation_id: str) -> AutomationConfirmationRequest | None:
        """Retrieve confirmation request status."""
        with self._lock:
            return self._pending_requests.get(confirmation_id)

    def cancel_all(self, reason: str = "Subsystem cancellation") -> None:
        """Cancel all pending confirmation requests."""
        with self._lock:
            for req in self._pending_requests.values():
                if req.status == AutomationConfirmationStatus.PENDING:
                    req.status = AutomationConfirmationStatus.CANCELLED
            logger.info(
                f"AutomationConfirmationManager: Cancelled all pending confirmations. Reason: {reason}"
            )
