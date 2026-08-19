"""Pre-defined declarative workflow examples for Phase 6.5 Workflow Engine."""

from app.automation.workflow.models import (
    ActionType,
    VerificationCondition,
    VerificationType,
    WorkflowAction,
    WorkflowExecutionMode,
    WorkflowPlan,
    WorkflowStep,
)


def build_open_project_explorer_workflow(
    project_path: str = "D:\\Friday AI",
    mode: WorkflowExecutionMode = WorkflowExecutionMode.SIMULATE,
) -> WorkflowPlan:
    """Build Example A: 'Open project in Explorer' declarative workflow plan."""
    return WorkflowPlan(
        workflow_id="wf_example_open_explorer",
        name="Open Project in File Explorer",
        description="Verifies project folder exists, launches Explorer, navigates to project, and verifies window focus.",
        execution_mode=mode,
        variables={"project_path": project_path},
        steps=[
            WorkflowStep(
                order=1,
                name="Validate Project Folder Exists",
                action=WorkflowAction(
                    action_type=ActionType.FILESYSTEM_CREATE_FOLDER,
                    target="{project_path}",
                    parameters={"folder_path": "{project_path}"},
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.FOLDER_EXISTS,
                    target="{project_path}",
                ),
            ),
            WorkflowStep(
                order=2,
                name="Launch or Attach Explorer",
                action=WorkflowAction(
                    action_type=ActionType.LAUNCH_APP,
                    target="explorer",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.PROCESS_RUNNING,
                    target="explorer",
                ),
            ),
            WorkflowStep(
                order=3,
                name="Navigate Explorer to Project Directory",
                action=WorkflowAction(
                    action_type=ActionType.NAVIGATE_EXPLORER,
                    target="{project_path}",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.EXPLORER_PATH_EQUALS,
                    target="{project_path}",
                    expected_value="{project_path}",
                ),
            ),
            WorkflowStep(
                order=4,
                name="Focus Explorer Window",
                action=WorkflowAction(
                    action_type=ActionType.FOCUS_WINDOW,
                    target="explorer",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.WINDOW_FOCUSED,
                    target="explorer",
                ),
            ),
        ],
    )


def build_open_project_terminal_workflow(
    project_path: str = "D:\\Friday AI",
    terminal_type: str = "cmd",
    mode: WorkflowExecutionMode = WorkflowExecutionMode.SIMULATE,
) -> WorkflowPlan:
    """Build Example B: 'Open project terminal' declarative workflow plan."""
    return WorkflowPlan(
        workflow_id="wf_example_open_terminal",
        name="Open Project Terminal",
        description="Validates project folder, launches target terminal, sets working directory, and focuses window.",
        execution_mode=mode,
        variables={"project_path": project_path, "terminal_type": terminal_type},
        steps=[
            WorkflowStep(
                order=1,
                name="Validate Project Folder Exists",
                action=WorkflowAction(
                    action_type=ActionType.FILESYSTEM_CREATE_FOLDER,
                    target="{project_path}",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.FOLDER_EXISTS,
                    target="{project_path}",
                ),
            ),
            WorkflowStep(
                order=2,
                name="Launch Terminal Subsystem",
                action=WorkflowAction(
                    action_type=ActionType.ATTACH_TERMINAL,
                    target="{terminal_type}",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.PROCESS_RUNNING,
                    target="{terminal_type}",
                ),
            ),
            WorkflowStep(
                order=3,
                name="Set Terminal Working Directory",
                action=WorkflowAction(
                    action_type=ActionType.SET_TERMINAL_CWD,
                    target="{project_path}",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.FOLDER_EXISTS,
                    target="{project_path}",
                ),
            ),
            WorkflowStep(
                order=4,
                name="Focus Terminal Window",
                action=WorkflowAction(
                    action_type=ActionType.FOCUS_WINDOW,
                    target="{terminal_type}",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.WINDOW_FOCUSED,
                    target="{terminal_type}",
                ),
            ),
        ],
    )


def build_arrange_workspace_workflow(
    mode: WorkflowExecutionMode = WorkflowExecutionMode.SIMULATE,
) -> WorkflowPlan:
    """Build Example C: 'Arrange workspace' declarative workflow plan using Phase 6.3 Desktop Control."""
    return WorkflowPlan(
        workflow_id="wf_example_arrange_workspace",
        name="Arrange Desktop Workspace",
        description="Inspects monitor topology, resolves windows, and snaps active window.",
        execution_mode=mode,
        steps=[
            WorkflowStep(
                order=1,
                name="Inspect Monitor Topology",
                action=WorkflowAction(
                    action_type=ActionType.GET_WORKSPACE_SUMMARY,
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.MONITOR_CONFIGURATION_AVAILABLE,
                ),
            ),
            WorkflowStep(
                order=2,
                name="Focus Target Window",
                action=WorkflowAction(
                    action_type=ActionType.FOCUS_WINDOW,
                    target="main",
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.WINDOW_FOCUSED,
                    target="main",
                ),
            ),
            WorkflowStep(
                order=3,
                name="Snap Window to Left Workarea",
                action=WorkflowAction(
                    action_type=ActionType.SNAP_WINDOW,
                    parameters={"position": "left"},
                ),
                verification=VerificationCondition(
                    condition_type=VerificationType.WINDOW_GEOMETRY_MATCH,
                ),
            ),
        ],
    )
