"""Pre-flight plan validator enforcing WorkflowPlan structural and semantic constraints."""

from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.errors import WorkflowInvalidError
from app.automation.workflow.models import (
    VerificationCondition,
    WorkflowPlan,
    WorkflowStep,
)
from app.automation.workflow.verifier_registry import VerificationRegistry


class WorkflowValidator:
    """Validator performing pre-flight structural, action, verifier, and safety validation on WorkflowPlan objects."""

    def __init__(
        self,
        action_registry: WorkflowActionRegistry | None = None,
        verifier_registry: VerificationRegistry | None = None,
    ) -> None:
        self.action_registry = action_registry or WorkflowActionRegistry()
        self.verifier_registry = verifier_registry or VerificationRegistry()

    def validate_plan(self, plan: WorkflowPlan) -> bool:
        """Perform comprehensive pre-flight plan validation. Raises WorkflowInvalidError if invalid."""
        if not plan.workflow_id or not plan.workflow_id.strip():
            raise WorkflowInvalidError(
                "Workflow plan must have a non-empty workflow_id."
            )

        if not plan.steps:
            raise WorkflowInvalidError(
                f"Workflow plan '{plan.workflow_id}' contains no steps."
            )

        if len(plan.steps) > plan.max_steps:
            raise WorkflowInvalidError(
                f"Workflow plan step count ({len(plan.steps)}) exceeds maximum allowed steps ({plan.max_steps}).",
                details={"step_count": len(plan.steps), "max_steps": plan.max_steps},
            )

        if plan.timeout_ms <= 0:
            raise WorkflowInvalidError(
                f"Workflow timeout_ms must be positive, got {plan.timeout_ms} ms."
            )

        # Validate step sequence orders
        orders = [step.order for step in plan.steps]
        if len(orders) != len(set(orders)):
            raise WorkflowInvalidError(
                f"Duplicate step orders detected in workflow plan '{plan.workflow_id}': {orders}"
            )

        # Validate individual steps
        for step in plan.steps:
            self._validate_step(step, plan)

        return True

    def _validate_step(self, step: WorkflowStep, plan: WorkflowPlan) -> None:
        """Validate individual WorkflowStep structure, action, and verifier conditions."""
        if not step.step_id or not step.step_id.strip():
            raise WorkflowInvalidError("Workflow step must have a non-empty step_id.")

        if not step.name or not step.name.strip():
            raise WorkflowInvalidError(
                f"Step '{step.step_id}' must have a non-empty name."
            )

        if step.timeout_ms <= 0:
            raise WorkflowInvalidError(
                f"Step '{step.step_id}' timeout_ms must be positive, got {step.timeout_ms} ms."
            )

        # Validate action
        if not self.action_registry.has_handler(step.action.action_type):
            raise WorkflowInvalidError(
                f"Step '{step.step_id}' references unregistered action type '{step.action.action_type.value}'.",
                details={
                    "step_id": step.step_id,
                    "action_type": step.action.action_type.value,
                },
            )

        # Validate precondition condition
        if step.precondition:
            self._validate_condition(step.precondition, step.step_id, "precondition")

        # Validate postcondition verification
        if step.verification:
            self._validate_condition(step.verification, step.step_id, "verification")

        # Validate retry policy bounds
        if step.retry_policy.max_attempts < 1 or step.retry_policy.max_attempts > 10:
            raise WorkflowInvalidError(
                f"Step '{step.step_id}' retry_policy max_attempts ({step.retry_policy.max_attempts}) must be between 1 and 10."
            )

        # Validate recovery policy bounds
        if (
            step.recovery_policy.max_recovery_attempts < 1
            or step.recovery_policy.max_recovery_attempts > 5
        ):
            raise WorkflowInvalidError(
                f"Step '{step.step_id}' recovery_policy max_recovery_attempts must be between 1 and 5."
            )

    def _validate_condition(
        self, cond: VerificationCondition, step_id: str, label: str
    ) -> None:
        """Validate verification condition type existence."""
        if cond.condition_type and not self.verifier_registry.has_evaluator(
            cond.condition_type
        ):
            raise WorkflowInvalidError(
                f"Step '{step_id}' {label} references unregistered verification type '{cond.condition_type}'.",
                details={
                    "step_id": step_id,
                    "condition_type": str(cond.condition_type),
                },
            )

        for sub in cond.sub_conditions:
            self._validate_condition(sub, step_id, label)
