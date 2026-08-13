"""Smoke test verifying clean application bootstrap sequence."""

from app.bootstrap.bootstrapper import AppBootstrapper


def test_smoke_bootstrap_sequence():
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()

        assert result.success is True
        assert result.container is not None
        assert result.settings is not None
        assert result.service_manager is not None
        assert result.main_window is not None
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
