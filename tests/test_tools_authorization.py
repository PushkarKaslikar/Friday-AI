"""Unit tests for DevAuthorizationProvider."""

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.security.authorization_provider import (
    AuthorizationStatus,
    DevAuthorizationProvider,
)


def test_dev_authorization_provider_modes():
    meta = ToolMetadata(
        tool_id="system.echo",
        name="echo",
        display_name="Echo",
        description="Echo tool",
        risk_level=ToolRiskLevel.LOW,
    )

    # ALLOW_ALL mode
    provider_allow = DevAuthorizationProvider(mode="ALLOW_ALL")
    res_allow = provider_allow.authorize_execution(meta)
    assert res_allow.status == AuthorizationStatus.AUTHORIZED

    # DENY_ALL mode
    provider_deny = DevAuthorizationProvider(mode="DENY_ALL")
    res_deny = provider_deny.authorize_execution(meta)
    assert res_deny.status == AuthorizationStatus.DENIED

    # REQUIRE_CONFIRMATION mode
    provider_conf = DevAuthorizationProvider(mode="REQUIRE_CONFIRMATION")
    res_conf = provider_conf.authorize_execution(meta)
    assert res_conf.status == AuthorizationStatus.CONFIRMATION_REQUIRED


def test_dev_authorization_provider_permissions():
    meta = ToolMetadata(
        tool_id="files.read",
        name="read_file",
        display_name="Read File",
        description="Read file tool",
        permissions=[ToolPermission.FILESYSTEM_READ],
        risk_level=ToolRiskLevel.LOW,
    )

    # Deny due to missing permission capability
    provider_no_perm = DevAuthorizationProvider(
        mode="DEFAULT", granted_permissions=set()
    )
    res_no_perm = provider_no_perm.authorize_execution(meta)
    assert res_no_perm.status == AuthorizationStatus.DENIED
    assert ToolPermission.FILESYSTEM_READ in res_no_perm.missing_permissions

    # Authorized when granted
    provider_perm = DevAuthorizationProvider(
        mode="DEFAULT", granted_permissions={ToolPermission.FILESYSTEM_READ}
    )
    res_perm = provider_perm.authorize_execution(meta)
    assert res_perm.status == AuthorizationStatus.AUTHORIZED
