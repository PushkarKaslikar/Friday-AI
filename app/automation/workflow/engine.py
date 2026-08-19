"""Workflow Engine managing deterministic, step-by-step verified workflow execution."""

import threading
import time
from typing import Any

from app.automation.input.input_engine import InputEngine
from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.context import WorkflowExecutionContext
from app.automation.workflow.errors import (
    FailsafeAbortedError,
    ResourceBusyError,
    WorkflowCancelledError,
    WorkflowInterruptedError,
    WorkflowTimeoutError,
)
from app.automation.workflow.events import (
    WorkflowAbortedEvent,
    WorkflowCancelledEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowInterruptedEvent,
    WorkflowPausedEvent,
    WorkflowResumedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowStepRecoveringEvent,
    WorkflowStepRetryingEvent,
    WorkflowStepStartedEvent,
    WorkflowStepVerificationStartedEvent,
    WorkflowStepVerifiedEvent,
    WorkflowValidatedEvent,
)
from app.automation.workflow.metrics import WorkflowMetrics
from app.automation.workflow.models import (
    ActionResult,
    FailurePolicy,
    RecoveryStrategy,
    StepResult,
    StepState,
    VerificationResult,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
)
from app.automation.workflow.validator import WorkflowValidator
from app.automation.workflow.verifier_registry import StepVerifier, VerificationRegistry
from app.events import EventBus
from app.logging import logger
from app.tools.execution.cancellation import CancellationToken


class WorkflowEngine:
    """Core multi-step workflow engine providing verified step-by-step automation execution."""

    def __init__(
        self,
        action_registry: WorkflowActionRegistry | None = None,
        verifier_registry: VerificationRegistry | None = None,
        validator: WorkflowValidator | None = None,
        step_verifier: StepVerifier | None = None,
        input_engine: InputEngine | None = None,
        event_bus: EventBus | None = None,
        metrics: WorkflowMetrics | None = None,
    ) -> None:
        self.action_registry = action_registry or WorkflowActionRegistry()
        self.verifier_registry = verifier_registry or VerificationRegistry()
        self.validator = validator or WorkflowValidator(
            self.action_registry, self.verifier_registry
        )
        self.step_verifier = step_verifier or StepVerifier(self.verifier_registry)
        self.input_engine = input_engine
        self.event_bus = event_bus
        self.metrics = metrics or WorkflowMetrics()

        self._lock = threading.Lock()
        self._active_live_workflow_id: str | None = None
        self._active_contexts: dict[str, WorkflowExecutionContext] = {}
        self._workflow_states: dict[str, WorkflowState] = {}
        self._paused_plans: dict[str, tuple[WorkflowPlan, int]] = {}

        # Subscribe to Phase 6.2 input interruption and failsafe signals if EventBus is present
        if self.event_bus:
            self.event_bus.subscribe(
                "InputOperationInterrupted", self._on_user_interruption_event
            )
            self.event_bus.subscribe("FailsafeTriggered", self._on_failsafe_event)

    def execute_workflow(
        self,
        plan: WorkflowPlan,
        cancellation_token: CancellationToken | None = None,
        initial_variables: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Execute a WorkflowPlan cleanly through the verified action-verify loop."""
        workflow_id = plan.workflow_id
        mode = plan.execution_mode

        # Enforce single LIVE workflow concurrency lock
        if mode == WorkflowExecutionMode.LIVE:
            with self._lock:
                if (
                    self._active_live_workflow_id
                    and self._active_live_workflow_id != workflow_id
                ):
                    self.metrics.increment_resource_busy()
                    raise ResourceBusyError(
                        f"A LIVE workflow ({self._active_live_workflow_id}) is currently executing. Cannot run concurrent LIVE workflow '{workflow_id}'.",
                        details={"active_workflow_id": self._active_live_workflow_id},
                    )
                self._active_live_workflow_id = workflow_id

        # Initialize execution state and context
        ctx = WorkflowExecutionContext(
            workflow_id=workflow_id,
            initial_variables=plan.variables | (initial_variables or {}),
            cancellation_token=cancellation_token or CancellationToken(),
        )

        with self._lock:
            self._active_contexts[workflow_id] = ctx
            self._workflow_states[workflow_id] = WorkflowState.VALIDATING

        self.metrics.increment_started()
        self._publish_event(
            "WorkflowStarted",
            WorkflowStartedEvent(
                workflow_id=workflow_id,
                name=plan.name,
                execution_mode=mode,
                total_steps=len(plan.steps),
            ),
        )

        t_start = time.perf_counter()
        step_results: list[StepResult] = []
        errors: list[str] = []
        retry_count = 0
        recovery_count = 0

        try:
            # 1. Pre-flight plan validation
            self.validator.validate_plan(plan)
            with self._lock:
                self._workflow_states[workflow_id] = WorkflowState.READY

            self._publish_event(
                "WorkflowValidated",
                WorkflowValidatedEvent(
                    workflow_id=workflow_id,
                    name=plan.name,
                    total_steps=len(plan.steps),
                    execution_mode=mode,
                ),
            )

            # 2. Transition to RUNNING
            with self._lock:
                self._workflow_states[workflow_id] = WorkflowState.RUNNING

            start_step_index = 0

            # Check if resuming from paused plan
            if workflow_id in self._paused_plans:
                resumed_plan, resume_index = self._paused_plans.pop(workflow_id)
                start_step_index = resume_index
                self._publish_event(
                    "WorkflowResumed",
                    WorkflowResumedEvent(
                        workflow_id=workflow_id,
                        resumed_from_step=resumed_plan.steps[resume_index].step_id,
                    ),
                )

            # Step-by-step verification execution loop
            for idx in range(start_step_index, len(plan.steps)):
                step = plan.steps[idx]

                # Check workflow timeout
                elapsed_wf_ms = (time.perf_counter() - t_start) * 1000.0
                if elapsed_wf_ms >= plan.timeout_ms:
                    self.metrics.increment_timeouts()
                    raise WorkflowTimeoutError(
                        f"Workflow '{workflow_id}' timed out after {elapsed_wf_ms:.1f} ms (limit: {plan.timeout_ms} ms).",
                        workflow_id=workflow_id,
                    )

                # Check cancellation
                if ctx.is_cancelled:
                    raise WorkflowCancelledError(
                        f"Workflow '{workflow_id}' cancelled by user request.",
                        workflow_id=workflow_id,
                    )

                # Execute step
                s_res = self._execute_step(step, ctx, plan, mode)
                step_results.append(s_res)
                retry_count += s_res.attempts - 1
                recovery_count += s_res.recovery_attempts

                if s_res.status == StepState.COMPLETED:
                    ctx.completed_steps.append(step.step_id)
                elif s_res.status == StepState.SKIPPED:
                    pass
                else:
                    ctx.failed_steps.append(step.step_id)
                    errors.append(
                        f"Step '{step.name}' ({step.step_id}) failed: {s_res.failure_reason}"
                    )

                    # Evaluate failure policy
                    if (
                        plan.failure_policy == FailurePolicy.FAIL_FAST
                        and not step.optional
                        and not step.continue_on_failure
                    ):
                        with self._lock:
                            self._workflow_states[workflow_id] = WorkflowState.FAILED
                        break

                    if plan.failure_policy == FailurePolicy.PAUSE_ON_FAILURE:
                        with self._lock:
                            self._workflow_states[workflow_id] = WorkflowState.PAUSED
                            self._paused_plans[workflow_id] = (plan, idx)
                        self._release_held_inputs()
                        self._publish_event(
                            "WorkflowPaused",
                            WorkflowPausedEvent(
                                workflow_id=workflow_id,
                                reason=s_res.failure_reason or "Pause on failure",
                                step_id=step.step_id,
                            ),
                        )
                        break

            # Calculate final workflow status
            final_duration_ms = (time.perf_counter() - t_start) * 1000.0
            completed_count = len(ctx.completed_steps)
            failed_count = len(ctx.failed_steps)

            with self._lock:
                current_st = self._workflow_states.get(
                    workflow_id, WorkflowState.RUNNING
                )

            if current_st in (
                WorkflowState.PAUSED,
                WorkflowState.INTERRUPTED,
                WorkflowState.ABORTED,
                WorkflowState.CANCELLED,
            ):
                final_state = current_st
            elif failed_count == 0:
                final_state = WorkflowState.COMPLETED
                self.metrics.increment_completed()
            elif completed_count > 0:
                final_state = WorkflowState.PARTIAL_SUCCESS
                self.metrics.increment_completed()
            else:
                final_state = WorkflowState.FAILED
                self.metrics.increment_failed()

            with self._lock:
                self._workflow_states[workflow_id] = final_state

            result = WorkflowResult(
                workflow_id=workflow_id,
                status=final_state,
                completed_steps=completed_count,
                failed_step=ctx.failed_steps[0] if ctx.failed_steps else None,
                duration_ms=final_duration_ms,
                outputs=ctx.get_all_variables(),
                errors=errors,
                verification_summary={
                    "completed": completed_count,
                    "failed": failed_count,
                },
                retry_count=retry_count,
                recovery_count=recovery_count,
                step_results=step_results,
            )

            self._publish_event(
                "WorkflowCompleted",
                WorkflowCompletedEvent(
                    workflow_id=workflow_id,
                    status=final_state,
                    completed_steps=completed_count,
                    duration_ms=final_duration_ms,
                ),
            )
            return result

        except Exception as exc:
            final_duration_ms = (time.perf_counter() - t_start) * 1000.0
            self._release_held_inputs()

            if isinstance(exc, WorkflowCancelledError):
                final_state = WorkflowState.CANCELLED
                self.metrics.increment_cancelled()
                self._publish_event(
                    "WorkflowCancelled",
                    WorkflowCancelledEvent(workflow_id=workflow_id, reason=str(exc)),
                )
            elif isinstance(exc, WorkflowInterruptedError):
                final_state = WorkflowState.INTERRUPTED
                self.metrics.increment_interrupted()
                self._publish_event(
                    "WorkflowInterrupted",
                    WorkflowInterruptedEvent(workflow_id=workflow_id, reason=str(exc)),
                )
            elif isinstance(exc, FailsafeAbortedError):
                final_state = WorkflowState.ABORTED
                self.metrics.increment_aborted()
                self._publish_event(
                    "WorkflowAborted",
                    WorkflowAbortedEvent(workflow_id=workflow_id, reason=str(exc)),
                )
            else:
                final_state = WorkflowState.FAILED
                self.metrics.increment_failed()
                self._publish_event(
                    "WorkflowFailed",
                    WorkflowFailedEvent(
                        workflow_id=workflow_id,
                        failed_step_id=(
                            ctx.failed_steps[0] if ctx.failed_steps else None
                        ),
                        reason=str(exc),
                        duration_ms=final_duration_ms,
                    ),
                )

            with self._lock:
                self._workflow_states[workflow_id] = final_state

            return WorkflowResult(
                workflow_id=workflow_id,
                status=final_state,
                completed_steps=len(ctx.completed_steps),
                failed_step=ctx.failed_steps[0] if ctx.failed_steps else None,
                duration_ms=final_duration_ms,
                outputs=ctx.get_all_variables(),
                errors=[str(exc)],
                retry_count=retry_count,
                recovery_count=recovery_count,
                step_results=step_results,
            )

        finally:
            with self._lock:
                if self._active_live_workflow_id == workflow_id:
                    self._active_live_workflow_id = None
                self._active_contexts.pop(workflow_id, None)

    def pause_workflow(
        self, workflow_id: str, reason: str = "User pause requested"
    ) -> bool:
        """Pause a running workflow cleanly."""
        with self._lock:
            if (
                workflow_id in self._workflow_states
                and self._workflow_states[workflow_id] == WorkflowState.RUNNING
            ):
                self._workflow_states[workflow_id] = WorkflowState.PAUSED
                self._release_held_inputs()
                self._publish_event(
                    "WorkflowPaused",
                    WorkflowPausedEvent(workflow_id=workflow_id, reason=reason),
                )
                return True
        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        with self._lock:
            if workflow_id in self._paused_plans:
                self._workflow_states[workflow_id] = WorkflowState.RUNNING
                return True
        return False

    def cancel_workflow(
        self, workflow_id: str, reason: str = "User cancellation requested"
    ) -> bool:
        """Cancel an active workflow cleanly."""
        with self._lock:
            ctx = self._active_contexts.get(workflow_id)
            if ctx:
                ctx.cancellation_token.request_cancellation(reason)
                self._workflow_states[workflow_id] = WorkflowState.CANCELLING
                self._release_held_inputs()
                return True
        return False

    def get_workflow_state(self, workflow_id: str) -> WorkflowState | None:
        """Query current workflow state."""
        with self._lock:
            return self._workflow_states.get(workflow_id)

    # Step Execution Core:

    def _execute_step(
        self,
        step: WorkflowStep,
        ctx: WorkflowExecutionContext,
        plan: WorkflowPlan,
        mode: WorkflowExecutionMode,
    ) -> StepResult:
        """Execute a single WorkflowStep with preconditions, actions, postcondition verifications, retries, and recovery."""
        t_step = time.perf_counter()
        self.metrics.increment_steps_executed()

        self._publish_event(
            "WorkflowStepStarted",
            WorkflowStepStartedEvent(
                workflow_id=plan.workflow_id,
                step_id=step.step_id,
                step_name=step.name,
                order=step.order,
                action_type=step.action.action_type.value,
            ),
        )

        # 1. Precondition Check
        if step.precondition:
            pre_res = self.step_verifier.verify_condition(step.precondition, ctx, mode)
            if pre_res.status != "PASSED":
                duration_ms = (time.perf_counter() - t_step) * 1000.0
                return StepResult(
                    step_id=step.step_id,
                    status=StepState.FAILED,
                    verification_result=pre_res,
                    duration_ms=duration_ms,
                    failure_reason=f"Precondition failed: {pre_res.reason}",
                )

        # Action execution with Retries & Recovery
        attempts = 0
        recovery_attempts = 0
        last_action_res: ActionResult | None = None
        last_verif_res: VerificationResult | None = None
        step_status = StepState.EXECUTING

        while attempts < step.retry_policy.max_attempts:
            attempts += 1

            if ctx.is_cancelled:
                raise WorkflowCancelledError(
                    "Cancelled during step execution.",
                    workflow_id=plan.workflow_id,
                    step_id=step.step_id,
                )

            # Resolve parameters via context variable templates
            resolved_action = WorkflowAction(
                action_type=step.action.action_type,
                target=(
                    ctx.resolve_value(step.action.target or "")
                    if step.action.target
                    else None
                ),
                parameters=ctx.resolve_dict(step.action.parameters),
                idempotent=step.action.idempotent,
            )

            # Execute action via registry
            last_action_res = self.action_registry.execute_action(
                resolved_action, ctx, mode
            )

            if last_action_res.status != "SUCCESS":
                if not step.retry_policy.is_idempotent or not step.action.idempotent:
                    logger.warning(
                        f"WorkflowEngine: Step '{step.name}' action is non-idempotent. Skipping retry."
                    )
                    break

                # Apply Retry delay / backoff if attempts remain
                if attempts < step.retry_policy.max_attempts:
                    self._apply_backoff(step.retry_policy, attempts)
                    self._publish_event(
                        "WorkflowStepRetrying",
                        WorkflowStepRetryingEvent(
                            workflow_id=plan.workflow_id,
                            step_id=step.step_id,
                            attempt=attempts,
                            max_attempts=step.retry_policy.max_attempts,
                            reason=last_action_res.error or "Action failed",
                        ),
                    )
                    continue

            # Action succeeded -> 2. Postcondition Verification
            self._publish_event(
                "WorkflowStepVerificationStarted",
                WorkflowStepVerificationStartedEvent(
                    workflow_id=plan.workflow_id,
                    step_id=step.step_id,
                    condition_type=(
                        str(step.verification.condition_type or "DEFAULT")
                        if step.verification
                        else "NONE"
                    ),
                ),
            )

            last_verif_res = self.step_verifier.verify_condition(
                step.verification, ctx, mode
            )
            self.metrics.increment_steps_verified()

            if last_verif_res.status == "PASSED":
                step_status = StepState.COMPLETED
                elapsed_val = float(getattr(last_verif_res, "elapsed_ms", 0.0) or 0.0)
                self._publish_event(
                    "WorkflowStepVerified",
                    WorkflowStepVerifiedEvent(
                        workflow_id=plan.workflow_id,
                        step_id=step.step_id,
                        condition_type=str(last_verif_res.condition_type or "PASSED"),
                        passed=True,
                        elapsed_ms=elapsed_val,
                    ),
                )

                # Record step output in context
                if last_action_res.output is not None:
                    ctx.record_step_output(
                        step.step_id, step.output_variable, last_action_res.output
                    )
                break

            # Verification Failed -> Attempt Recovery if allowed
            if recovery_attempts < step.recovery_policy.max_recovery_attempts:
                recovery_attempts += 1
                rec_success = self._attempt_recovery(step, ctx, mode)
                self.metrics.increment_recoveries()
                self._publish_event(
                    "WorkflowStepRecovering",
                    WorkflowStepRecoveringEvent(
                        workflow_id=plan.workflow_id,
                        step_id=step.step_id,
                        strategy=step.recovery_policy.strategy.value,
                        attempt=recovery_attempts,
                    ),
                )
                if rec_success:
                    # Re-verify condition after successful recovery
                    last_verif_res = self.step_verifier.verify_condition(
                        step.verification, ctx, mode
                    )
                    if last_verif_res.status == "PASSED":
                        step_status = StepState.COMPLETED
                        break  # Retry step after successful recovery strategy execution

        duration_ms = (time.perf_counter() - t_step) * 1000.0

        if step_status != StepState.COMPLETED and (
            step.optional or step.continue_on_failure
        ):
            step_status = StepState.SKIPPED

        s_res = StepResult(
            step_id=step.step_id,
            status=step_status,
            action_result=last_action_res,
            verification_result=last_verif_res,
            attempts=attempts,
            duration_ms=duration_ms,
            failure_reason=(
                last_action_res.error
                if last_action_res and last_action_res.error
                else (
                    last_verif_res.reason if last_verif_res else "Step execution failed"
                )
            ),
            recovery_attempts=recovery_attempts,
        )

        self._publish_event(
            "WorkflowStepCompleted",
            WorkflowStepCompletedEvent(
                workflow_id=plan.workflow_id,
                step_id=step.step_id,
                step_name=step.name,
                order=step.order,
                status=step_status,
                duration_ms=duration_ms,
            ),
        )

        return s_res

    def _attempt_recovery(
        self,
        step: WorkflowStep,
        ctx: WorkflowExecutionContext,
        mode: WorkflowExecutionMode,
    ) -> bool:
        """Attempt step recovery strategy."""
        strat = step.recovery_policy.strategy
        if strat == RecoveryStrategy.ABORT:
            return False
        if (
            strat == RecoveryStrategy.REFOCUS
            and ctx.active_hwnd
            and self.action_registry.desktop_controller
        ):
            self.action_registry.desktop_controller.window_controller.focus_window(
                ctx.active_hwnd
            )
            return True
        if strat in (
            RecoveryStrategy.RE_RESOLVE_TARGET,
            RecoveryStrategy.REATTACH,
            RecoveryStrategy.REFRESH_UI,
        ):
            return True
        return False

    def _apply_backoff(self, policy: Any, attempt: int) -> None:
        """Apply delay / backoff between retries."""
        if policy.delay_ms <= 0:
            return
        delay_sec = policy.delay_ms / 1000.0
        if policy.backoff == "EXPONENTIAL":
            delay_sec *= 2 ** (attempt - 1)
        time.sleep(min(delay_sec, 5.0))

    def _release_held_inputs(self) -> None:
        """Helper to release held physical inputs via InputEngine."""
        if self.input_engine:
            try:
                self.input_engine.release_all_inputs()
            except Exception as exc:
                logger.warning(f"WorkflowEngine: Failed to release inputs: {exc}")

    def _on_user_interruption_event(self, event_data: Any) -> None:
        """EventBus handler for Phase 6.2 physical user input interruption signal."""
        logger.warning("WorkflowEngine: Physical user input interruption received!")
        self._release_held_inputs()
        with self._lock:
            if self._active_live_workflow_id:
                self._workflow_states[self._active_live_workflow_id] = (
                    WorkflowState.INTERRUPTED
                )

    def _on_failsafe_event(self, event_data: Any) -> None:
        """EventBus handler for Phase 6.2 top-left mouse emergency failsafe signal."""
        logger.critical("WorkflowEngine: Emergency mouse failsafe triggered!")
        self._release_held_inputs()
        with self._lock:
            if self._active_live_workflow_id:
                self._workflow_states[self._active_live_workflow_id] = (
                    WorkflowState.ABORTED
                )

    def _publish_event(self, event_type: str, data: Any) -> None:
        """Publish event via EventBus if available."""
        if self.event_bus:
            try:
                self.event_bus.publish(data)
            except Exception:
                try:
                    self.event_bus.publish(event_type, data)
                except Exception as exc:
                    logger.warning(
                        f"WorkflowEngine: Failed to publish '{event_type}' event: {exc}"
                    )
