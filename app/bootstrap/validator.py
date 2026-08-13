"""Environment validator ensuring all system prerequisites are met prior to application launch."""

import sys
from typing import NamedTuple

from app.constants.application import MIN_PYTHON_VERSION
from app.constants.paths import LOGS_DIR, REQUIRED_DIRECTORIES, SETTINGS_FILE
from app.exceptions.bootstrap import EnvironmentValidationError
from app.utilities.path_utils import (
    ensure_directory_exists,
    is_directory_writable,
    is_path_readable,
)
from app.utilities.system_utils import is_python_version_supported


class ValidationResult(NamedTuple):
    is_valid: bool
    errors: list[str]


class EnvironmentValidator:
    """Validates runtime environment, filesystem permissions, Python version, and config readability."""

    def validate_all(self) -> ValidationResult:
        """Run all environment validation checks.

        Returns:
            ValidationResult: Object containing pass status and list of any error messages.
        """
        errors: list[str] = []

        # 1. Python Version Check
        if not is_python_version_supported():
            current_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            min_ver = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
            errors.append(
                f"Unsupported Python version: {current_ver}. Requires Python >= {min_ver}."
            )

        # 2. Required Directories Check & Creation
        for directory in REQUIRED_DIRECTORIES:
            try:
                ensure_directory_exists(directory)
            except OSError as exc:
                errors.append(
                    f"Failed to create or verify required directory '{directory}': {exc}"
                )

        # 3. Log Directory Write Permissions Check
        if not is_directory_writable(LOGS_DIR):
            errors.append(
                f"Log directory '{LOGS_DIR}' is not writable. Check file permissions."
            )

        # 4. Settings File Readability (if file exists)
        if SETTINGS_FILE.exists() and not is_path_readable(SETTINGS_FILE):
            errors.append(
                f"Settings file '{SETTINGS_FILE}' exists but is not readable."
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_or_raise(self) -> None:
        """Run all validation checks and raise EnvironmentValidationError if any check fails."""
        result = self.validate_all()
        if not result.is_valid:
            error_msg = (
                "Environment validation failed with the following errors:\n"
                + "\n".join(f"  - {err}" for err in result.errors)
            )
            raise EnvironmentValidationError(
                error_msg, details={"errors": result.errors}
            )
