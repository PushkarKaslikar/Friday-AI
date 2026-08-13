"""Unit tests for ToolMetadata, RiskLevel, and PermissionRequirement validation."""

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import PermissionRequirement, ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.categories import ToolCategory


def test_tool_metadata_validation():
    meta = ToolMetadata(
        tool_id="system.echo",
        name="echo",
        display_name="Echo Tool",
        description="Echoes message for testing",
        category=ToolCategory.SYSTEM,
        risk_level=ToolRiskLevel.LOW,
        permissions=[ToolPermission.FILESYSTEM_READ],
    )
    assert meta.tool_id == "system.echo"
    assert meta.risk_level == ToolRiskLevel.LOW
    assert ToolPermission.FILESYSTEM_READ in meta.permissions
    assert meta.confirmation_required is False


def test_permission_requirement_default_deny():
    req = PermissionRequirement(
        required_permissions=[
            ToolPermission.FILESYSTEM_READ,
            ToolPermission.FILESYSTEM_WRITE,
        ],
        default_deny=True,
    )

    # Partial permissions
    granted = {ToolPermission.FILESYSTEM_READ}
    authorized, missing = req.validate_permissions(granted)
    assert authorized is False
    assert missing == [ToolPermission.FILESYSTEM_WRITE]

    # Full permissions
    granted_all = {ToolPermission.FILESYSTEM_READ, ToolPermission.FILESYSTEM_WRITE}
    auth_ok, missing_none = req.validate_permissions(granted_all)
    assert auth_ok is True
    assert missing_none == []
