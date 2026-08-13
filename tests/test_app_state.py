"""Unit tests for AppStateManager."""

from app.services.state.state_manager import ApplicationState, AppStateManager


def test_app_state_manager_transitions():
    sm = AppStateManager()
    sm.set_state(ApplicationState.STARTUP)
    assert sm.current_state == ApplicationState.STARTUP

    sm.set_state(ApplicationState.RUNNING)
    assert sm.current_state == ApplicationState.RUNNING

    sm.set_state(ApplicationState.MINIMIZED)
    assert sm.current_state == ApplicationState.MINIMIZED

    sm.set_state(ApplicationState.SHUTTING_DOWN)
    assert sm.current_state == ApplicationState.SHUTTING_DOWN
