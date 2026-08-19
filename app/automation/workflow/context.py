"""Workflow Execution Context holding variable state, active attachments, and cancellation tokens."""

import time
from typing import Any

from app.automation.workflow.errors import VariableInvalidError
from app.tools.execution.cancellation import CancellationToken
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class WorkflowExecutionContext:
    """Encapsulates execution context state, variable bindings, and safe variable resolution."""

    def __init__(
        self,
        workflow_id: str,
        initial_variables: dict[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self._variables: dict[str, Any] = (
            initial_variables.copy() if initial_variables else {}
        )
        self.cancellation_token = cancellation_token or CancellationToken()
        self.completed_steps: list[str] = []
        self.failed_steps: list[str] = []
        self.step_outputs: dict[str, Any] = {}
        self.active_hwnd: int | None = None
        self.active_app_id: str | None = None
        self.active_pid: int | None = None
        self.start_time: float = time.time()

    def set_variable(self, name: str, value: Any) -> None:
        """Bind variable name to structured value cleanly without code execution."""
        clean_name = name.strip()
        if not clean_name:
            raise VariableInvalidError("Variable name cannot be empty.")

        # Disallow python keywords / syntax injection
        if any(char in clean_name for char in ["(", ")", ";", "=", " ", "\n", "\t"]):
            raise VariableInvalidError(f"Invalid variable name syntax: '{name}'")

        self._variables[clean_name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Retrieve bound variable value."""
        return self._variables.get(name.strip(), default)

    def has_variable(self, name: str) -> bool:
        """Check if variable exists in context."""
        return name.strip() in self._variables

    def get_all_variables(self) -> dict[str, Any]:
        """Return a safe copy of all variables."""
        return self._variables.copy()

    def get_sanitized_variables(self) -> dict[str, Any]:
        """Return variables with sensitive values masked."""
        sanitized: dict[str, Any] = {}
        for key, val in self._variables.items():
            if isinstance(val, str):
                sanitized[key] = SensitiveDataSanitizer.sanitize_text(val)
            else:
                sanitized[key] = val
        return sanitized

    def resolve_value(self, raw_val: Any) -> Any:
        """Resolve value or string template variable reference cleanly (e.g. '{project_path}' or '$project_path')."""
        if not isinstance(raw_val, str):
            return raw_val

        val_str = raw_val.strip()
        # Single variable reference check: {var_name}
        if (
            val_str.startswith("{")
            and val_str.endswith("}")
            and val_str.count("{") == 1
        ):
            var_name = val_str[1:-1].strip()
            if var_name in self._variables:
                return self._variables[var_name]

        # Single variable reference check: $var_name
        if (
            val_str.startswith("$")
            and " " not in val_str
            and val_str[1:] in self._variables
        ):
            return self._variables[val_str[1:]]

        # Template string substitution for embedded variables
        resolved = val_str
        for var_name, var_val in self._variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in resolved:
                resolved = resolved.replace(placeholder, str(var_val))
            dollar_placeholder = f"${var_name}"
            if dollar_placeholder in resolved:
                resolved = resolved.replace(dollar_placeholder, str(var_val))

        return resolved

    def resolve_dict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively resolve variables in dictionary parameters."""
        resolved: dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, dict):
                resolved[k] = self.resolve_dict(v)
            elif isinstance(v, list):
                resolved[k] = [self.resolve_value(item) for item in v]
            else:
                resolved[k] = self.resolve_value(v)
        return resolved

    def record_step_output(
        self, step_id: str, variable_name: str | None, output: Any
    ) -> None:
        """Record step output and optionally export as a context variable."""
        self.step_outputs[step_id] = output
        if variable_name and variable_name.strip():
            self.set_variable(variable_name, output)

    @property
    def is_cancelled(self) -> bool:
        """Check if execution has been cancelled."""
        return self.cancellation_token.is_cancelled
