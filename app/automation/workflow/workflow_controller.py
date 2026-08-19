"""Main coordinator service for Phase 6.5 Workflow Engine Subsystem."""

from typing import Any

from app.automation.apps.apps_controller import ApplicationAdapterManager
from app.automation.desktop.desktop_controller import DesktopController
from app.automation.input.input_engine import InputEngine
from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.diagnostics import WorkflowDiagnostics
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.metrics import WorkflowMetrics
from app.automation.workflow.models import (
    WorkflowPlan,
    WorkflowResult,
    WorkflowState,
)
from app.automation.workflow.validator import WorkflowValidator
from app.automation.workflow.verifier_registry import StepVerifier, VerificationRegistry
from app.events import EventBus
from app.logging import logger
from app.platform.filesystem.filesystem_service import FilesystemService
from app.tools.execution.cancellation import CancellationToken


class WorkflowManager:
    """Main coordinator service uniting WorkflowEngine, registries, validator, metrics, and diagnostics."""

    def __init__(
        self,
        app_manager: ApplicationAdapterManager | None = None,
        desktop_controller: DesktopController | None = None,
        input_engine: InputEngine | None = None,
        filesystem_service: FilesystemService | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.app_manager = app_manager
        self.desktop_controller = desktop_controller
        self.input_engine = input_engine
        self.filesystem_service = filesystem_service
        self.event_bus = event_bus

        self.action_registry = WorkflowActionRegistry(
            app_manager=app_manager,
            desktop_controller=desktop_controller,
            input_engine=input_engine,
            filesystem_service=filesystem_service,
        )
        self.verifier_registry = VerificationRegistry()
        self.step_verifier = StepVerifier(
            registry=self.verifier_registry,
            app_manager=app_manager,
            desktop_controller=desktop_controller,
        )
        self.validator = WorkflowValidator(self.action_registry, self.verifier_registry)
        self.metrics = WorkflowMetrics()

        self.engine = WorkflowEngine(
            action_registry=self.action_registry,
            verifier_registry=self.verifier_registry,
            validator=self.validator,
            step_verifier=self.step_verifier,
            input_engine=input_engine,
            event_bus=event_bus,
            metrics=self.metrics,
        )

        self.diagnostics = WorkflowDiagnostics(
            engine=self.engine,
            action_registry=self.action_registry,
            verifier_registry=self.verifier_registry,
            metrics=self.metrics,
        )

        logger.info("WorkflowManager initialized successfully in IDLE state.")

    def execute_plan(
        self,
        plan: WorkflowPlan,
        cancellation_token: CancellationToken | None = None,
        variables: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Validate and execute a WorkflowPlan through WorkflowEngine."""
        return self.engine.execute_workflow(
            plan=plan,
            cancellation_token=cancellation_token,
            initial_variables=variables,
        )

    def validate_plan(self, plan: WorkflowPlan) -> bool:
        """Validate WorkflowPlan without execution."""
        return self.validator.validate_plan(plan)

    def pause_workflow(
        self, workflow_id: str, reason: str = "User requested pause"
    ) -> bool:
        """Pause a running workflow."""
        return self.engine.pause_workflow(workflow_id, reason)

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        return self.engine.resume_workflow(workflow_id)

    def cancel_workflow(
        self, workflow_id: str, reason: str = "User requested cancellation"
    ) -> bool:
        """Cancel a running workflow."""
        return self.engine.cancel_workflow(workflow_id, reason)

    def get_workflow_state(self, workflow_id: str) -> WorkflowState | None:
        """Query workflow status state."""
        return self.engine.get_workflow_state(workflow_id)

    def get_health_report(self) -> dict[str, Any]:
        """Generate subsystem diagnostic health report."""
        return self.diagnostics.get_health_report()
