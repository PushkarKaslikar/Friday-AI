"""Application bootstrapper managing the 8-stage startup sequence."""

import sys
from typing import NamedTuple

from PySide6.QtWidgets import QApplication

from app.bootstrap.validator import EnvironmentValidator
from app.build.validator import ProductionValidator
from app.config.manager import ConfigurationManager
from app.config.models import Settings
from app.crash.crash_handler import CrashHandler
from app.dependency.container import ApplicationContainer
from app.diagnostics.system_diagnostics import SystemDiagnostics
from app.exceptions.bootstrap import InitializationError
from app.logging import LoggingManager, logger
from app.monitoring.performance_monitor import PerformanceMonitor
from app.platform.notifications.notification_manager import NotificationManager
from app.platform.resources.resource_monitor import ResourceMonitor
from app.plugins.loader.plugin_loader import PluginLoader
from app.services.core.service_manager import ServiceManager
from app.services.events.event_bus import EventBus
from app.services.events.event_models import ApplicationStarted, ApplicationStopped
from app.services.health.health_monitor import HealthMonitor
from app.services.scheduler.scheduler_service import SchedulerService
from app.services.state.state_manager import ApplicationState, AppStateManager
from app.services.threading.thread_manager import ThreadManager
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.registry.tool_registry import ToolRegistry
from app.ui.managers.tray_manager import TrayManager
from app.ui.managers.window_manager import WindowManager
from app.ui.navigation.navigation_manager import NavigationManager
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager
from app.ui.windows.main_window import MainWindow
from app.ui.windows.splash_screen import SplashScreen


class BootstrapResult(NamedTuple):
    success: bool
    container: ApplicationContainer
    settings: Settings
    logging_manager: LoggingManager
    qt_app: QApplication
    main_window: MainWindow
    tray_manager: TrayManager
    service_manager: ServiceManager


class AppBootstrapper:
    """Orchestrates the formal 8-step application startup process."""

    def __init__(
        self,
        validator: EnvironmentValidator | None = None,
        container: ApplicationContainer | None = None,
    ) -> None:
        self.validator = validator or EnvironmentValidator()
        self.container = container or ApplicationContainer()
        self.settings: Settings | None = None
        self.logging_manager: LoggingManager | None = None
        self.qt_app: QApplication | None = None
        self.splash: SplashScreen | None = None
        self.main_window: MainWindow | None = None
        self.tray_manager: TrayManager | None = None
        self.service_manager: ServiceManager | None = None

    def run(self, is_cli: bool | None = None) -> BootstrapResult:
        """Executes all 8 startup phases sequentially."""
        if is_cli is None:
            is_cli = ("pytest" in sys.modules) or (
                len(sys.argv) > 1 and sys.argv[0].endswith("main.py")
            )
        try:
            self.container.reset_singletons()

            # Install crash handler early
            crash_handler: CrashHandler = self.container.crash_handler()
            crash_handler.install()

            # Ensure Qt Application instance exists
            self._ensure_qt_app()

            # Step 1: Validate environment & production readiness
            self._step1_validate_environment()

            # Step 2: Load configuration
            self._step2_load_configuration()

            # Step 3: Initialize logging
            self._step3_initialize_logging()

            # Step 4: Build dependency container & show Splash Screen
            self._step4_build_dependency_container(is_cli=is_cli)

            # Step 5: Register & start core background services, tool registry & executor
            self._step5_register_services()

            # Step 6: Validate application state & discover plugins
            self._step6_validate_application_state()

            # Step 7: Prepare UI framework & Main Window
            self._step7_prepare_ui_initialization()

            # Step 8: Report successful startup & display UI / Tray
            self._step8_report_startup_success(is_cli=is_cli)

            assert self.settings is not None
            assert self.logging_manager is not None
            assert self.qt_app is not None
            assert self.main_window is not None
            assert self.tray_manager is not None
            assert self.service_manager is not None

            return BootstrapResult(
                success=True,
                container=self.container,
                settings=self.settings,
                logging_manager=self.logging_manager,
                qt_app=self.qt_app,
                main_window=self.main_window,
                tray_manager=self.tray_manager,
                service_manager=self.service_manager,
            )
        except Exception as exc:
            if self.splash:
                self.splash.close()
            if not isinstance(exc, InitializationError):
                raise InitializationError(
                    f"Application bootstrap failed during startup sequence: {exc}",
                    cause=exc,
                ) from exc
            raise

    def _ensure_qt_app(self) -> None:
        """Ensure QApplication instance is initialized."""
        if QApplication.instance() is None:
            self.qt_app = QApplication(sys.argv)
            self.qt_app.setApplicationName("Friday AI Assistant")
        else:
            self.qt_app = QApplication.instance()

    def _step1_validate_environment(self) -> None:
        """Step 1: Validate system environment, paths, permissions, and production readiness."""
        self.validator.validate_or_raise()

        prod_validator: ProductionValidator = self.container.production_validator()
        check = prod_validator.run_all_checks()
        if not check.passed:
            logger.warning(f"Production readiness warnings: {check.failures}")

    def _step2_load_configuration(self) -> None:
        """Step 2: Load application settings from config sources."""
        config_manager: ConfigurationManager = self.container.config_manager()
        self.settings = config_manager.load_settings()

    def _step3_initialize_logging(self) -> None:
        """Step 3: Initialize Loguru logging sinks and log startup header."""
        assert self.settings is not None
        self.logging_manager = LoggingManager(settings=self.settings.logging)
        self.logging_manager.setup_logging()
        self.logging_manager.log_startup(
            app_name=self.settings.app.name,
            version=self.settings.app.version,
            environment=self.settings.app.environment,
        )
        logger.info("[Bootstrap Step 3/8] Logging system initialized successfully.")

    def _step4_build_dependency_container(self, is_cli: bool = False) -> None:
        """Step 4: Build Dependency Injection container & display Splash Screen if not CLI mode."""
        theme_manager: ThemeManager = self.container.theme_manager()
        asset_manager: AssetManager = self.container.asset_manager()

        self.splash = SplashScreen(
            theme_manager=theme_manager, asset_manager=asset_manager
        )
        if not is_cli:
            self.splash.show()
            self.splash.update_progress(40, "Wiring Dependency Injection Container...")
        logger.info("[Bootstrap Step 4/8] Dependency Injection container wired.")

    def _step5_register_services(self) -> None:
        """Step 5: Register and start core background services, ToolRegistry and ToolExecutor."""
        if self.splash:
            self.splash.update_progress(
                60, "Registering Windows System Tools & Executor..."
            )

        self.service_manager = self.container.service_manager()
        scheduler_service: SchedulerService = self.container.scheduler_service()
        health_monitor: HealthMonitor = self.container.health_monitor()
        perf_monitor: PerformanceMonitor = self.container.performance_monitor()
        res_monitor: ResourceMonitor = self.container.resource_monitor()
        sys_diagnostics: SystemDiagnostics = self.container.system_diagnostics()
        tool_executor: ToolExecutor = self.container.tool_executor()

        audio_engine = self.container.audio_engine()
        clap_detector = self.container.clap_detector()
        wakeword_detector = self.container.wakeword_detector()
        vad_detector = self.container.vad_detector()
        stt_service = self.container.stt_service()
        tts_service = self.container.tts_service()
        conversation_sm = self.container.conversation_state_machine()
        conversation_manager = self.container.conversation_manager()
        greeting_service = self.container.greeting_service()
        llm_model_manager = self.container.llm_model_manager()
        ai_orchestrator = self.container.ai_orchestrator()
        tool_calling_engine = self.container.tool_calling_engine()
        personality_engine = self.container.personality_engine()
        response_generator = self.container.response_generator()
        uia_engine = self.container.ui_automation_engine()
        try:
            uia_engine.initialize()
        except Exception as uia_exc:
            logger.warning(f"UI Automation Engine non-fatal startup warning: {uia_exc}")

        # Register background services
        self.service_manager.register_service(scheduler_service)
        self.service_manager.register_service(health_monitor)
        self.service_manager.register_service(perf_monitor)
        self.service_manager.register_service(res_monitor)
        self.service_manager.register_service(sys_diagnostics)
        self.service_manager.register_service(tool_executor)
        self.service_manager.register_service(audio_engine)
        self.service_manager.register_service(clap_detector)
        self.service_manager.register_service(wakeword_detector)
        self.service_manager.register_service(vad_detector)
        self.service_manager.register_service(stt_service)
        self.service_manager.register_service(tts_service)
        self.service_manager.register_service(conversation_sm)
        self.service_manager.register_service(conversation_manager)
        self.service_manager.register_service(greeting_service)
        self.service_manager.register_service(llm_model_manager)
        self.service_manager.register_service(ai_orchestrator)
        self.service_manager.register_service(tool_calling_engine)
        self.service_manager.register_service(personality_engine)
        self.service_manager.register_service(response_generator)

        # Register all 75 Core System & Browser Tools into ToolRegistry
        tool_registry: ToolRegistry = self.container.tool_registry()

        tools_to_register = [
            # Core Demo Tools
            self.container.echo_tool(),
            self.container.application_info_tool(),
            self.container.runtime_status_tool(),
            # System Info Tools
            self.container.cpu_info_tool(),
            self.container.memory_info_tool(),
            self.container.disk_info_tool(),
            self.container.windows_info_tool(),
            self.container.uptime_tool(),
            self.container.current_user_tool(),
            # Application Tools
            self.container.open_application_tool(),
            self.container.close_application_tool(),
            self.container.application_status_tool(),
            # File & Folder Tools
            self.container.open_file_tool(),
            self.container.open_folder_tool(),
            self.container.file_exists_tool(),
            self.container.folder_exists_tool(),
            self.container.file_info_tool(),
            self.container.folder_info_tool(),
            self.container.create_file_tool(),
            self.container.create_folder_tool(),
            self.container.copy_file_tool(),
            self.container.copy_folder_tool(),
            self.container.list_directory_tool(),
            self.container.calculate_size_tool(),
            # Filesystem Mutation & Workspace Tools
            self.container.move_file_tool(),
            self.container.move_folder_tool(),
            self.container.rename_file_tool(),
            self.container.rename_folder_tool(),
            self.container.delete_file_tool(),
            self.container.delete_folder_tool(),
            self.container.search_files_tool(),
            self.container.hash_file_tool(),
            self.container.compare_files_tool(),
            self.container.workspace_info_tool(),
            self.container.recent_files_tool(),
            self.container.batch_operation_tool(),
            # Browser Tools
            self.container.open_browser_tool(),
            self.container.open_url_tool(),
            self.container.browser_status_tool(),
            self.container.current_page_tool(),
            self.container.get_title_tool(),
            self.container.get_page_text_tool(),
            self.container.get_page_info_tool(),
            self.container.get_links_tool(),
            self.container.list_tabs_tool(),
            self.container.active_tab_tool(),
            self.container.new_tab_tool(),
            self.container.switch_tab_tool(),
            self.container.close_tab_tool(),
            self.container.browser_back_tool(),
            self.container.browser_forward_tool(),
            self.container.browser_reload_tool(),
            self.container.focus_browser_tool(),
            self.container.browser_search_tool(),
            # Process Tools
            self.container.process_list_tool(),
            self.container.process_info_tool(),
            self.container.process_running_tool(),
            self.container.terminate_process_tool(),
            # Audio Tools
            self.container.get_volume_tool(),
            self.container.set_volume_tool(),
            self.container.mute_audio_tool(),
            self.container.unmute_audio_tool(),
            # Clipboard Tools
            self.container.read_clipboard_tool(),
            self.container.write_clipboard_tool(),
            # Window Management Tools
            self.container.window_list_tool(),
            self.container.active_window_tool(),
            self.container.focus_window_tool(),
            self.container.minimize_window_tool(),
            self.container.maximize_window_tool(),
            self.container.restore_window_tool(),
            self.container.close_window_tool(),
            # Power Management Tools
            self.container.lock_computer_tool(),
            self.container.sleep_computer_tool(),
            self.container.restart_computer_tool(),
            self.container.shutdown_computer_tool(),
        ]

        for t in tools_to_register:
            tool_registry.register_tool(t)

        # Register health monitor targets
        health_monitor.register_service(scheduler_service)
        health_monitor.register_service(perf_monitor)
        health_monitor.register_service(res_monitor)
        health_monitor.register_service(sys_diagnostics)
        health_monitor.register_service(tool_executor)
        health_monitor.register_service(audio_engine)
        health_monitor.register_service(clap_detector)
        health_monitor.register_service(wakeword_detector)
        health_monitor.register_service(vad_detector)
        health_monitor.register_service(stt_service)
        health_monitor.register_service(tts_service)
        health_monitor.register_service(conversation_sm)
        health_monitor.register_service(conversation_manager)
        health_monitor.register_service(greeting_service)
        health_monitor.register_service(llm_model_manager)
        health_monitor.register_service(ai_orchestrator)
        health_monitor.register_service(tool_calling_engine)
        health_monitor.register_service(personality_engine)
        health_monitor.register_service(response_generator)

        # Initialize and start core services
        self.service_manager.initialize_all()
        self.service_manager.start_all()

        logger.info(
            f"[Bootstrap Step 5/8] Core services started. Registered tools: {tool_registry.registered_count}."
        )

    def _step6_validate_application_state(self) -> None:
        """Step 6: Validate application state & discover external plugins."""
        assert self.settings is not None
        if not self.settings.app.name:
            raise InitializationError(
                "Application name in configuration cannot be empty."
            )
        if self.splash:
            self.splash.update_progress(80, "Discovering & Validating Plugins...")

        plugin_loader: PluginLoader = self.container.plugin_loader()
        loaded_plugins = plugin_loader.discover_and_load()
        logger.info(
            f"[Bootstrap Step 6/8] Application state validated. Plugins discovered: {loaded_plugins}."
        )

    def _step7_prepare_ui_initialization(self) -> None:
        """Step 7: Prepare UI framework, Main Window, and System Tray."""
        if self.splash:
            self.splash.update_progress(95, "Initializing Desktop UI & System Tray...")

        theme_manager: ThemeManager = self.container.theme_manager()
        asset_manager: AssetManager = self.container.asset_manager()
        window_manager: WindowManager = self.container.window_manager()
        navigation_manager: NavigationManager = self.container.navigation_manager()
        self.tray_manager = self.container.tray_manager()
        notification_manager: NotificationManager = (
            self.container.notification_manager()
        )

        # Initialize Main Window
        self.main_window = MainWindow(
            theme_manager=theme_manager,
            asset_manager=asset_manager,
            navigation_manager=navigation_manager,
            window_manager=window_manager,
        )
        window_manager.register_window("main", self.main_window)

        # Setup System Tray
        self.tray_manager.setup_tray()

        # Connect Tray actions
        self.tray_manager.show_requested.connect(
            lambda: window_manager.show_window("main")
        )
        self.tray_manager.hide_requested.connect(
            lambda: window_manager.hide_window("main")
        )
        self.tray_manager.settings_requested.connect(self.main_window.open_settings)
        self.tray_manager.exit_requested.connect(self._on_tray_exit)

        # Emit startup toast notification
        notification_manager.show_info(
            title="Friday AI Assistant",
            message="Friday AI Assistant initialized and active.",
        )

        logger.info("[Bootstrap Step 7/8] PySide6 UI initialization completed.")

    def _step8_report_startup_success(self, is_cli: bool = False) -> None:
        """Step 8: Close Splash Screen, update AppStateManager, and display UI / Tray if not CLI mode."""
        assert self.settings is not None
        assert self.main_window is not None

        if self.splash and not is_cli:
            self.splash.update_progress(100, "Ready!")
            self.splash.finish(self.main_window)

        # Transition Application State to RUNNING
        state_manager: AppStateManager = self.container.app_state_manager()
        state_manager.set_state(ApplicationState.RUNNING)

        # Publish ApplicationStarted event
        event_bus: EventBus = self.container.event_bus()
        event_bus.publish(
            ApplicationStarted(
                app_name=self.settings.app.name,
                version=self.settings.app.version,
                environment=self.settings.app.environment,
            )
        )

        if not is_cli:
            if not self.settings.ui.start_minimized:
                self.main_window.show()
            else:
                state_manager.set_state(ApplicationState.MINIMIZED)
                logger.info("Starting minimized to system tray per configuration.")

        logger.info(
            f"[Bootstrap Step 8/8] Application {self.settings.app.name} v{self.settings.app.version} initialization complete."
        )

    def _on_tray_exit(self) -> None:
        """Handle explicit exit requested from system tray context menu."""
        logger.info("Exit requested from System Tray.")

        # Transition Application State to SHUTTING_DOWN
        state_manager: AppStateManager = self.container.app_state_manager()
        state_manager.set_state(ApplicationState.SHUTTING_DOWN)

        # Publish ApplicationStopped event
        event_bus: EventBus = self.container.event_bus()
        event_bus.publish(
            ApplicationStopped(app_name=self.settings.app.name, reason="user_tray_exit")
        )

        # Stop & shutdown background services
        if self.service_manager:
            self.service_manager.shutdown_all()

        # Shutdown worker thread pool
        thread_manager: ThreadManager = self.container.thread_manager()
        thread_manager.shutdown(wait=True)

        window_manager: WindowManager = self.container.window_manager()
        window_manager.close_all()

        if self.tray_manager:
            self.tray_manager.hide()

        state_manager.set_state(ApplicationState.STOPPED)

        if self.qt_app:
            self.qt_app.quit()
