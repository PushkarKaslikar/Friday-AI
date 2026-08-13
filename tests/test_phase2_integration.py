"""Integration test suite for Phase 2 validating end-to-end command execution pipelines, workflows, and tool discovery."""

import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.tools.categories import ToolCategory
from app.tools.discovery.tool_discovery import ToolDiscoveryService
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.errors import ToolErrorCode
from app.tools.models.request import ToolRequest
from app.tools.registry.tool_registry import ToolRegistry
from app.tools.security.authorization_provider import DevAuthorizationProvider


@pytest.fixture(scope="module")
def app_bootstrap():
    """Module-level fixture initializing full application container & tool registry."""
    bootstrapper = AppBootstrapper()
    result = bootstrapper.run()
    return result


def test_integration_application_to_tool_executor(app_bootstrap):
    """Test A: End-to-end pipeline from ToolRequest -> ToolExecutor -> ToolRegistry -> ToolResult."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()
    registry: ToolRegistry = container.tool_registry()

    assert registry.registered_count == 75

    request = ToolRequest(
        tool_id="system.echo",
        arguments={"message": "Integration Pipeline Test"},
    )

    result = executor.execute_request(request)
    assert result.success is True
    assert result.result_data["echoed_text"] == "Integration Pipeline Test"


def test_integration_filesystem_workflow(tmp_path, app_bootstrap):
    """Test B: Multi-step filesystem workflow executing through ToolExecutor."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()
    auth_provider: DevAuthorizationProvider = container.dev_authorization_provider()
    original_mode = auth_provider.mode
    auth_provider.mode = "ALLOW_ALL"

    try:
        workspace_dir = tmp_path / "integration_workspace"

        # Step 1: Create Folder
        res_mkdir = executor.execute_request(
            ToolRequest(
                tool_id="files.create_folder", arguments={"path": str(workspace_dir)}
            )
        )
        assert res_mkdir.success is True

        # Step 2: Create File
        file_path = workspace_dir / "sample.txt"
        res_mkfile = executor.execute_request(
            ToolRequest(
                tool_id="files.create_file",
                arguments={
                    "path": str(file_path),
                    "content": "Friday Integration Test Content",
                },
            )
        )
        assert res_mkfile.success is True

        # Step 3: Get File Info
        res_info = executor.execute_request(
            ToolRequest(
                tool_id="files.get_file_info", arguments={"path": str(file_path)}
            )
        )
        assert res_info.success is True
        assert "filename" in res_info.result_data

        # Step 4: Calculate Hash
        res_hash = executor.execute_request(
            ToolRequest(tool_id="files.hash_file", arguments={"path": str(file_path)})
        )
        assert res_hash.success is True
        assert "hash_value" in res_hash.result_data

        # Step 5: Rename File
        res_rename = executor.execute_request(
            ToolRequest(
                tool_id="files.rename_file",
                arguments={"path": str(file_path), "new_name": "renamed_sample.txt"},
            )
        )
        assert res_rename.success is True
        renamed_path = workspace_dir / "renamed_sample.txt"
        assert renamed_path.exists()

        # Step 6: Move File
        dest_dir = tmp_path / "destination_dir"
        executor.execute_request(
            ToolRequest(
                tool_id="files.create_folder", arguments={"path": str(dest_dir)}
            )
        )
        res_move = executor.execute_request(
            ToolRequest(
                tool_id="files.move_file",
                arguments={"source": str(renamed_path), "destination": str(dest_dir)},
            )
        )
        assert res_move.success is True
        moved_path = dest_dir / "renamed_sample.txt"
        assert moved_path.exists()

        # Step 7: Delete File (Recycle Bin fallback in test)
        res_delete = executor.execute_request(
            ToolRequest(
                tool_id="files.delete_file",
                arguments={"path": str(moved_path), "use_recycle_bin": False},
            )
        )
        assert res_delete.success is True
        assert not moved_path.exists()
    finally:
        auth_provider.mode = original_mode


def test_integration_browser_workflow(app_bootstrap):
    """Test C: Multi-step browser workflow executing through ToolExecutor."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()

    # Step 1: Open Browser
    res_open = executor.execute_request(
        ToolRequest(tool_id="browser.open", arguments={"browser_type": "chrome"})
    )
    assert res_open.success is True
    assert res_open.result_data["is_running"] is True

    # Step 2: Open URL
    res_nav = executor.execute_request(
        ToolRequest(tool_id="browser.open_url", arguments={"url": "https://python.org"})
    )
    assert res_nav.success is True

    # Step 3: New Tab
    res_tab = executor.execute_request(
        ToolRequest(
            tool_id="browser.new_tab", arguments={"url": "https://docs.python.org"}
        )
    )
    assert res_tab.success is True
    tab2_id = res_tab.result_data["tab_id"]

    # Step 4: List Tabs
    res_list = executor.execute_request(
        ToolRequest(tool_id="browser.list_tabs", arguments={})
    )
    assert res_list.success is True
    assert res_list.result_data["tab_count"] >= 1

    # Step 5: Close Tab
    res_close = executor.execute_request(
        ToolRequest(tool_id="browser.close_tab", arguments={"tab_id": tab2_id})
    )
    assert res_close.success is True
    assert res_close.result_data["closed"] is True


def test_integration_authorization_pipeline(app_bootstrap):
    """Test D: Authorization provider integration enforcing ALLOW and DENY rules."""
    container = app_bootstrap.container
    auth_provider: DevAuthorizationProvider = container.dev_authorization_provider()
    executor: ToolExecutor = container.tool_executor()

    # Configure explicit authorization mode
    auth_provider.mode = "DENY_ALL"

    req = ToolRequest(tool_id="system.echo", arguments={"message": "Auth Test"})
    res_denied = executor.execute_request(req)
    assert res_denied.success is False
    assert res_denied.error_code == ToolErrorCode.PERMISSION_DENIED

    # Reset mode to DEFAULT
    auth_provider.mode = "DEFAULT"
    res_allowed = executor.execute_request(req)
    assert res_allowed.success is True


def test_integration_tool_discovery_service(app_bootstrap):
    """Test F: ToolDiscoveryService category, tag, risk, and fuzzy search filtering."""
    container = app_bootstrap.container
    discovery: ToolDiscoveryService = container.tool_discovery_service()

    # Filter by category
    files_tools = discovery.find_by_category(ToolCategory.FILES)
    assert len(files_tools) >= 15

    media_tools = discovery.find_by_category(ToolCategory.MEDIA)
    assert len(media_tools) >= 18

    # Filter by tag
    search_tools = discovery.find_by_tag("search")
    assert len(search_tools) >= 2

    # Fuzzy search
    res_fuzzy = discovery.search_tools("delete folder")
    assert len(res_fuzzy) >= 1
    assert res_fuzzy[0].tool_id == "files.delete_folder"
