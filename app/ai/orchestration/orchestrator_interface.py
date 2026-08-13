"""Abstract boundary contract for AI Orchestrator.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

from abc import ABC, abstractmethod

from app.ai.orchestration.models import (
    OrchestrationRequest,
    OrchestrationResult,
    OrchestratorConfiguration,
    OrchestratorState,
)


class IAIOrchestrator(ABC):
    """Abstract interface contract for AI Orchestrator & Reasoning Workflow Engine."""

    @abstractmethod
    def process_request(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Process user request through multi-step AI reasoning and tool workflow.

        Args:
            request: OrchestrationRequest containing user input and session context

        Returns:
            OrchestrationResult: Structured outcome with final response and executed tools
        """

    @property
    @abstractmethod
    def state(self) -> OrchestratorState:
        """Return current orchestrator lifecycle state."""

    @property
    @abstractmethod
    def orchestrator_config(self) -> OrchestratorConfiguration:
        """Return active configuration settings."""
