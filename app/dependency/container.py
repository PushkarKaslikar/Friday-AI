"""Dependency Injection container using dependency-injector."""

from dependency_injector import containers, providers

from app.ai.diagnostics.diagnostics import LLMDiagnostics
from app.automation.models import MatchMode
from app.automation.apps.apps_controller import ApplicationAdapterManager
from app.automation.apps.diagnostics import ApplicationAdapterDiagnostics
from app.automation.apps.explorer_adapter import ExplorerAdapter
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.metrics import ApplicationAdapterMetrics
from app.automation.apps.registry import ApplicationAdapterRegistry
from app.automation.apps.terminal_adapter import TerminalAdapter
from app.automation.workflow.action_registry import WorkflowActionRegistry
from app.automation.workflow.diagnostics import WorkflowDiagnostics
from app.automation.workflow.engine import WorkflowEngine
from app.automation.workflow.metrics import WorkflowMetrics
from app.automation.workflow.validator import WorkflowValidator
from app.automation.workflow.verifier_registry import StepVerifier, VerificationRegistry
from app.automation.workflow.workflow_controller import WorkflowManager
from app.tools.builtin.automation import (
    ApplicationAttachTool,
    ApplicationLaunchTool,
    ApplicationStatusTool as AutomationApplicationStatusTool,
    AutomationToolDiagnostics,
    AutomationToolMetrics,
    ClipboardGetContentTool,
    ClipboardSetContentTool,
    ExplorerNavigateTool,
    ExplorerOpenItemTool,
    InputMouseClickTool,
    InputPressHotkeyTool,
    InputTypeTextTool,
    ScreenCaptureTool,
    ScreenListMonitorsTool,
    TerminalLaunchTool,
    TerminalReadOutputTool,
    UiaFindElementTool,
    UiaInspectWindowTool,
    UiaListWindowsTool,
    WindowFocusTool as AutomationWindowFocusTool,
    WindowListOpenTool,
    WindowMaximizeTool as AutomationWindowMaximizeTool,
    WindowSnapTool,
    WorkflowExecuteSequenceTool,
)
from app.automation.safety import (
    AutomationAuditLog,
    AutomationConfirmationManager,
    AutomationKillSwitch,
    AutomationSafetyAnalyzer,
    AutomationSafetyDiagnostics,
    AutomationSafetyManager,
    AutomationSafetyMetrics,
    AutomationSafetyPolicy,
)
from app.automation.desktop.clipboard_manager import ClipboardManager
from app.automation.desktop.desktop_controller import DesktopController
from app.automation.desktop.diagnostics import DesktopDiagnostics
from app.automation.desktop.metrics import DesktopMetrics
from app.automation.desktop.monitor_manager import MonitorManager
from app.automation.desktop.screen_capturer import ScreenCapturer
from app.automation.desktop.virtual_desktop import VirtualDesktopManager
from app.automation.desktop.window_controller import WindowController
from app.automation.desktop.workspace_manager import WorkspaceManager
from app.automation.input.diagnostics import InputDiagnostics
from app.automation.input.failsafe import InputFailsafe
from app.automation.input.input_engine import InputEngine
from app.automation.input.interruption_monitor import InterruptionMonitor
from app.automation.input.metrics import InputMetrics
from app.automation.input.native_input import NativeInputBackend
from app.automation.input.pyautogui_fallback import PyAutoGUIInputBackend
from app.automation.input.target_resolver import TargetResolver
from app.automation.uia.diagnostics import UIAutomationDiagnostics
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.metrics import UIAutomationMetrics
from app.automation.uia.tree_walker import UITreeWalker
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver
from app.ai.gateway.model_manager import LLMModelManager
from app.ai.metrics.metrics import LLMMetrics
from app.ai.orchestration.ai_orchestrator import AIOrchestrator
from app.ai.orchestration.diagnostics import OrchestratorDiagnostics
from app.ai.orchestration.metrics import OrchestratorMetrics
from app.ai.personality.behavioral_rules import BehavioralRulesEngine
from app.ai.personality.diagnostics import PersonalityDiagnostics
from app.ai.personality.emotional_classifier import EmotionalSignalClassifier
from app.ai.personality.metrics import PersonalityMetrics
from app.ai.personality.personality_engine import PersonalityEngine
from app.ai.providers.fake_provider import FakeAIModelProvider
from app.ai.providers.llama_cpp_provider import LlamaCppProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.response.context_builder import ResponseContextBuilder
from app.ai.response.diagnostics import ResponseGenerationDiagnostics
from app.ai.response.metrics import ResponseGenerationMetrics
from app.ai.response.response_generator import ResponseGenerator
from app.ai.response.strategy_selector import ResponseStrategySelector
from app.ai.response.validator_normalizer import ResponseValidatorNormalizer
from app.ai.tool_calling.diagnostics import ToolCallingDiagnostics
from app.ai.tool_calling.metrics import ToolCallingMetrics
from app.ai.tool_calling.provider_adapter import DefaultToolCallAdapter
from app.ai.tool_calling.schema_registry import ToolSchemaRegistry
from app.ai.tool_calling.tool_calling_engine import ToolCallingEngine
from app.build.build_config import BuildConfig
from app.build.validator import ProductionValidator
from app.config.backup_manager import ConfigBackupManager
from app.config.manager import ConfigurationManager
from app.config.migrator import ConfigMigrator
from app.crash.crash_handler import CrashHandler
from app.diagnostics.system_diagnostics import SystemDiagnostics
from app.error.error_manager import ErrorManager
from app.logging import LoggingManager
from app.memory.context_builder import MemoryContextBuilder
from app.memory.db_manager import MemoryDatabaseManager
from app.memory.diagnostics import MemoryDiagnostics
from app.memory.embedding_provider import LocalEmbeddingProvider
from app.memory.long_term_diagnostics import LongTermMemoryDiagnostics
from app.memory.long_term_metrics import LongTermMemoryMetrics
from app.memory.long_term_service import LongTermMemoryService
from app.memory.metrics import MemoryMetrics
from app.memory.privacy_diagnostics import MemoryPrivacyDiagnostics
from app.memory.privacy_metrics import MemoryPrivacyMetrics
from app.memory.privacy_policy import MemoryPrivacyPolicy
from app.memory.privacy_service import MemoryPrivacyService
from app.memory.profile_diagnostics import UserProfileDiagnostics
from app.memory.profile_metrics import UserProfileMetrics
from app.memory.profile_service import UserProfileService
from app.memory.promotion_service import MemoryPromotionService
from app.memory.query_builder import MemoryQueryBuilder
from app.memory.ranking_service import MemoryRankingService
from app.memory.repository import SQLAlchemyMemoryRepository
from app.memory.retention_service import MemoryRetentionService
from app.memory.retrieval_diagnostics import MemoryRetrievalDiagnostics
from app.memory.retrieval_metrics import MemoryRetrievalMetrics
from app.memory.retrieval_policy import MemoryRetrievalPolicy
from app.memory.retrieval_service import MemoryRetrievalService
from app.memory.semantic_diagnostics import SemanticMemoryDiagnostics
from app.memory.semantic_index import FAISSMemoryIndex
from app.memory.semantic_metrics import SemanticMemoryMetrics
from app.memory.semantic_service import SemanticMemoryService
from app.memory.service import ShortTermMemoryService
from app.memory.session_diagnostics import SessionMemoryDiagnostics
from app.memory.session_metrics import SessionMemoryMetrics
from app.memory.session_service import SessionMemoryService
from app.memory.store import ShortTermMemoryStore
from app.memory.text_builder import MemoryEmbeddingTextBuilder
from app.monitoring.performance_monitor import PerformanceMonitor
from app.platform.browser.browser_service import BrowserService
from app.platform.browser.url_security import UrlSecurityManager
from app.platform.filesystem.filesystem_service import FilesystemService
from app.platform.filesystem.path_security import PathSecurityManager
from app.platform.info.system_info import SystemInfo
from app.platform.notifications.notification_manager import NotificationManager
from app.platform.process.process_manager import ProcessManager
from app.platform.registry.registry_manager import RegistryManager
from app.platform.resources.resource_monitor import ResourceMonitor
from app.platform.startup.startup_manager import StartupManager
from app.platform.version.version_manager import VersionManager
from app.plugins.loader.plugin_loader import PluginLoader
from app.plugins.registry.plugin_registry import PluginRegistry
from app.plugins.validation.plugin_validator import PluginValidator
from app.services.core.service_manager import ServiceManager
from app.services.events.event_bus import EventBus
from app.services.health.health_monitor import HealthMonitor
from app.services.messages.message_dispatcher import MessageDispatcher
from app.services.scheduler.scheduler_service import SchedulerService
from app.services.state.state_manager import AppStateManager
from app.services.threading.thread_manager import ThreadManager
from app.settings.user_settings_manager import UserSettingsManager
from app.tools.builtin import (
    ActiveTabTool,
    ActiveWindowTool,
    ApplicationInfoTool,
    ApplicationStatusTool,
    BatchOperationTool,
    BrowserBackTool,
    BrowserForwardTool,
    BrowserReloadTool,
    BrowserSearchTool,
    BrowserStatusTool,
    CalculateSizeTool,
    CloseApplicationTool,
    CloseTabTool,
    CloseWindowTool,
    CompareFilesTool,
    CopyFileTool,
    CopyFolderTool,
    CpuInfoTool,
    CreateFileTool,
    CreateFolderTool,
    CurrentPageTool,
    CurrentUserTool,
    DeleteFileTool,
    DeleteFolderTool,
    DiskInfoTool,
    EchoTool,
    FileExistsTool,
    FileInfoTool,
    FocusBrowserTool,
    FocusWindowTool,
    FolderExistsTool,
    FolderInfoTool,
    GetLinksTool,
    GetPageInfoTool,
    GetPageTextTool,
    GetTitleTool,
    GetVolumeTool,
    HashFileTool,
    ListDirectoryTool,
    ListTabsTool,
    LockComputerTool,
    MaximizeWindowTool,
    MemoryInfoTool,
    MinimizeWindowTool,
    MoveFileTool,
    MoveFolderTool,
    MuteAudioTool,
    NewTabTool,
    OpenApplicationTool,
    OpenBrowserTool,
    OpenFileTool,
    OpenFolderTool,
    OpenUrlTool,
    ProcessInfoTool,
    ProcessListTool,
    ProcessRunningTool,
    ReadClipboardTool,
    RecentFilesTool,
    RenameFileTool,
    RenameFolderTool,
    RestartComputerTool,
    RestoreWindowTool,
    RuntimeStatusTool,
    SearchFilesTool,
    SetVolumeTool,
    ShutdownComputerTool,
    SleepComputerTool,
    SwitchTabTool,
    TerminateProcessTool,
    UnmuteAudioTool,
    UptimeTool,
    WindowListTool,
    WindowsInfoTool,
    WorkspaceInfoTool,
    WriteClipboardTool,
)
from app.tools.discovery.tool_discovery import ToolDiscoveryService
from app.tools.execution.execution_metrics import ExecutionMetrics
from app.tools.execution.execution_tracker import ExecutionTracker
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.registry.tool_registry import ToolRegistry
from app.tools.security.authorization_provider import DevAuthorizationProvider
from app.ui.managers.tray_manager import TrayManager
from app.ui.managers.ui_state_manager import UIStateManager
from app.ui.managers.window_manager import WindowManager
from app.ui.navigation.navigation_manager import NavigationManager
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.device_manager import AudioDeviceManager
from app.voice.audio.diagnostics import AudioDiagnostics
from app.voice.audio.metrics import AudioMetrics
from app.voice.clap.clap_detector import ClapDetector
from app.voice.clap.diagnostics import ClapDiagnostics
from app.voice.clap.metrics import ClapMetrics
from app.voice.conversation.context_builder import ContextBuilder
from app.voice.conversation.conversation_manager import (
    ConversationManager,
    ManagerResponseProvider,
)
from app.voice.conversation.conversation_store import InMemConversationStore
from app.voice.conversation.diagnostics import ConversationDiagnostics
from app.voice.conversation.manager_diagnostics import ConversationManagerDiagnostics
from app.voice.conversation.manager_metrics import ConversationManagerMetrics
from app.voice.conversation.metrics import ConversationMetrics
from app.voice.conversation.orchestrating_response_provider import (
    OrchestratingResponseProvider,
)
from app.voice.conversation.reference_resolver import DeterministicReferenceResolver
from app.voice.conversation.state_machine import ConversationStateMachine
from app.voice.conversation.test_response_provider import TestResponseProvider
from app.voice.greeting.ai_greeting_provider import AIGreetingProvider
from app.voice.greeting.diagnostics import GreetingDiagnostics
from app.voice.greeting.greeting_context_builder import GreetingContextBuilder
from app.voice.greeting.greeting_selector import GreetingSelector
from app.voice.greeting.greeting_service import GreetingService
from app.voice.greeting.metrics import GreetingMetrics
from app.voice.greeting.template_provider import TemplateGreetingProvider
from app.voice.stt.diagnostics import STTDiagnostics
from app.voice.stt.faster_whisper_engine import FasterWhisperSTTEngine
from app.voice.stt.metrics import STTMetrics
from app.voice.stt.stt_service import STTService
from app.voice.tts.diagnostics import TTSDiagnostics
from app.voice.tts.metrics import TTSMetrics
from app.voice.tts.piper_tts_provider import PiperTTSProvider
from app.voice.tts.tts_service import TTSService
from app.voice.vad.diagnostics import VADDiagnostics
from app.voice.vad.metrics import VADMetrics
from app.voice.vad.silero_vad_model import SileroVADModel
from app.voice.vad.vad_detector import VADDetector
from app.voice.wakeword.diagnostics import WakeWordDiagnostics
from app.voice.wakeword.metrics import WakeWordMetrics
from app.voice.wakeword.model_provider import WakeWordModelProvider
from app.voice.wakeword.wakeword_detector import WakeWordDetector


class ApplicationContainer(containers.DeclarativeContainer):
    """Main Dependency Injection container for the application."""

    # Configuration Manager singleton
    config_manager = providers.Singleton(
        ConfigurationManager,
    )

    # Loaded Settings provider object
    settings = providers.Callable(
        lambda cm: cm.settings,
        cm=config_manager,
    )

    # Config Backup Manager singleton
    config_backup_manager = providers.Singleton(
        ConfigBackupManager,
    )

    # Config Migrator singleton
    config_migrator = providers.Singleton(
        ConfigMigrator,
    )

    # User Settings Manager singleton
    user_settings_manager = providers.Singleton(
        UserSettingsManager,
        backup_manager=config_backup_manager,
    )

    # Logging Settings sub-provider
    logging_settings = providers.Callable(
        lambda s: s.logging,
        s=settings,
    )

    # Logging Manager singleton
    logging_manager = providers.Singleton(
        LoggingManager,
        settings=logging_settings,
    )

    # Core Event Bus singleton
    event_bus = providers.Singleton(
        EventBus,
    )

    # Error Manager singleton
    error_manager = providers.Singleton(
        ErrorManager,
        event_bus=event_bus,
    )

    # Crash Handler singleton
    crash_handler = providers.Singleton(
        CrashHandler,
    )

    # Registry Manager singleton
    registry_manager = providers.Singleton(
        RegistryManager,
    )

    # Startup Manager singleton
    startup_manager = providers.Singleton(
        StartupManager,
        registry_manager=registry_manager,
    )

    # Version Manager singleton
    version_manager = providers.Singleton(
        VersionManager,
    )

    # System Info singleton
    system_info = providers.Singleton(
        SystemInfo,
    )

    # Process Manager singleton
    process_manager = providers.Singleton(
        ProcessManager,
    )

    # Path Security Manager singleton
    path_security_manager = providers.Singleton(
        PathSecurityManager,
    )

    # Filesystem Service singleton
    filesystem_service = providers.Singleton(
        FilesystemService,
        security_manager=path_security_manager,
    )

    # URL Security Manager singleton
    url_security_manager = providers.Singleton(
        UrlSecurityManager,
    )

    # Browser Service singleton
    browser_service = providers.Singleton(
        BrowserService,
        url_security=url_security_manager,
    )

    # Build Config singleton
    build_config = providers.Singleton(
        BuildConfig,
    )

    # Production Validator singleton
    production_validator = providers.Singleton(
        ProductionValidator,
    )

    # Thread Manager singleton
    thread_manager = providers.Singleton(
        ThreadManager,
    )

    # Performance Monitor service singleton
    performance_monitor = providers.Singleton(
        PerformanceMonitor,
    )

    # Resource Monitor service singleton
    resource_monitor = providers.Singleton(
        ResourceMonitor,
    )

    # Application State Manager singleton
    app_state_manager = providers.Singleton(
        AppStateManager,
    )

    # Message Dispatcher singleton
    message_dispatcher = providers.Singleton(
        MessageDispatcher,
    )

    # Scheduler Service singleton
    scheduler_service = providers.Singleton(
        SchedulerService,
    )

    # Health Monitor singleton
    health_monitor = providers.Singleton(
        HealthMonitor,
        event_bus=event_bus,
        thread_manager=thread_manager,
    )

    # Service Manager singleton
    service_manager = providers.Singleton(
        ServiceManager,
        event_bus=event_bus,
    )

    # Tool Registry singleton
    tool_registry = providers.Singleton(
        ToolRegistry,
        event_bus=event_bus,
    )

    # Tool Discovery Service singleton
    tool_discovery_service = providers.Singleton(
        ToolDiscoveryService,
        registry=tool_registry,
    )

    # Core Builtin Tools Singletons
    echo_tool = providers.Singleton(EchoTool)
    application_info_tool = providers.Singleton(ApplicationInfoTool)
    runtime_status_tool = providers.Singleton(
        RuntimeStatusTool, service_manager=service_manager
    )

    # System Info Tools
    cpu_info_tool = providers.Singleton(CpuInfoTool)
    memory_info_tool = providers.Singleton(MemoryInfoTool)
    disk_info_tool = providers.Singleton(DiskInfoTool)
    windows_info_tool = providers.Singleton(WindowsInfoTool)
    uptime_tool = providers.Singleton(UptimeTool)
    current_user_tool = providers.Singleton(CurrentUserTool)

    # Application Tools
    open_application_tool = providers.Singleton(OpenApplicationTool)
    close_application_tool = providers.Singleton(
        CloseApplicationTool, process_manager=process_manager
    )
    application_status_tool = providers.Singleton(ApplicationStatusTool)

    # File & Folder Tools
    open_file_tool = providers.Singleton(OpenFileTool)
    open_folder_tool = providers.Singleton(OpenFolderTool)
    file_exists_tool = providers.Singleton(FileExistsTool)
    folder_exists_tool = providers.Singleton(FolderExistsTool)
    file_info_tool = providers.Singleton(FileInfoTool)
    folder_info_tool = providers.Singleton(FolderInfoTool)
    create_file_tool = providers.Singleton(CreateFileTool, service=filesystem_service)
    create_folder_tool = providers.Singleton(
        CreateFolderTool, service=filesystem_service
    )
    copy_file_tool = providers.Singleton(CopyFileTool, service=filesystem_service)
    copy_folder_tool = providers.Singleton(CopyFolderTool, service=filesystem_service)
    list_directory_tool = providers.Singleton(
        ListDirectoryTool, service=filesystem_service
    )
    calculate_size_tool = providers.Singleton(
        CalculateSizeTool, service=filesystem_service
    )

    # Filesystem Mutation & Workspace Tools
    move_file_tool = providers.Singleton(MoveFileTool, service=filesystem_service)
    move_folder_tool = providers.Singleton(MoveFolderTool, service=filesystem_service)
    rename_file_tool = providers.Singleton(RenameFileTool, service=filesystem_service)
    rename_folder_tool = providers.Singleton(
        RenameFolderTool, service=filesystem_service
    )
    delete_file_tool = providers.Singleton(DeleteFileTool, service=filesystem_service)
    delete_folder_tool = providers.Singleton(
        DeleteFolderTool, service=filesystem_service
    )
    search_files_tool = providers.Singleton(SearchFilesTool, service=filesystem_service)
    hash_file_tool = providers.Singleton(HashFileTool, service=filesystem_service)
    compare_files_tool = providers.Singleton(
        CompareFilesTool, service=filesystem_service
    )
    workspace_info_tool = providers.Singleton(
        WorkspaceInfoTool, service=filesystem_service
    )
    recent_files_tool = providers.Singleton(RecentFilesTool)
    batch_operation_tool = providers.Singleton(
        BatchOperationTool, service=filesystem_service
    )

    # Browser Tools
    open_browser_tool = providers.Singleton(OpenBrowserTool, service=browser_service)
    open_url_tool = providers.Singleton(OpenUrlTool, service=browser_service)
    browser_status_tool = providers.Singleton(
        BrowserStatusTool, service=browser_service
    )
    current_page_tool = providers.Singleton(CurrentPageTool, service=browser_service)
    get_title_tool = providers.Singleton(GetTitleTool, service=browser_service)
    get_page_text_tool = providers.Singleton(GetPageTextTool, service=browser_service)
    get_page_info_tool = providers.Singleton(GetPageInfoTool, service=browser_service)
    get_links_tool = providers.Singleton(GetLinksTool, service=browser_service)
    list_tabs_tool = providers.Singleton(ListTabsTool, service=browser_service)
    active_tab_tool = providers.Singleton(ActiveTabTool, service=browser_service)
    new_tab_tool = providers.Singleton(NewTabTool, service=browser_service)
    switch_tab_tool = providers.Singleton(SwitchTabTool, service=browser_service)
    close_tab_tool = providers.Singleton(CloseTabTool, service=browser_service)
    browser_back_tool = providers.Singleton(BrowserBackTool, service=browser_service)
    browser_forward_tool = providers.Singleton(
        BrowserForwardTool, service=browser_service
    )
    browser_reload_tool = providers.Singleton(
        BrowserReloadTool, service=browser_service
    )
    focus_browser_tool = providers.Singleton(FocusBrowserTool, service=browser_service)
    browser_search_tool = providers.Singleton(
        BrowserSearchTool, service=browser_service
    )

    # Process Tools
    process_list_tool = providers.Singleton(ProcessListTool)
    process_info_tool = providers.Singleton(ProcessInfoTool)
    process_running_tool = providers.Singleton(ProcessRunningTool)
    terminate_process_tool = providers.Singleton(
        TerminateProcessTool, process_manager=process_manager
    )

    # Audio Tools
    get_volume_tool = providers.Singleton(GetVolumeTool)
    set_volume_tool = providers.Singleton(SetVolumeTool)
    mute_audio_tool = providers.Singleton(MuteAudioTool)
    unmute_audio_tool = providers.Singleton(UnmuteAudioTool)

    # Clipboard Tools
    read_clipboard_tool = providers.Singleton(ReadClipboardTool)
    write_clipboard_tool = providers.Singleton(WriteClipboardTool)

    # Window Management Tools
    window_list_tool = providers.Singleton(WindowListTool)
    active_window_tool = providers.Singleton(ActiveWindowTool)
    focus_window_tool = providers.Singleton(FocusWindowTool)
    minimize_window_tool = providers.Singleton(MinimizeWindowTool)
    maximize_window_tool = providers.Singleton(MaximizeWindowTool)
    restore_window_tool = providers.Singleton(RestoreWindowTool)
    close_window_tool = providers.Singleton(CloseWindowTool)

    # Power Management Tools
    lock_computer_tool = providers.Singleton(LockComputerTool)
    sleep_computer_tool = providers.Singleton(SleepComputerTool)
    restart_computer_tool = providers.Singleton(RestartComputerTool)
    shutdown_computer_tool = providers.Singleton(ShutdownComputerTool)

    # Dev Authorization Provider singleton
    dev_authorization_provider = providers.Singleton(
        DevAuthorizationProvider,
    )

    # Execution Tracker singleton
    execution_tracker = providers.Singleton(
        ExecutionTracker,
    )

    # Execution Metrics singleton
    execution_metrics = providers.Singleton(
        ExecutionMetrics,
    )

    # Tool Executor service singleton
    tool_executor = providers.Singleton(
        ToolExecutor,
        registry=tool_registry,
        event_bus=event_bus,
        auth_provider=dev_authorization_provider,
        tracker=execution_tracker,
        metrics=execution_metrics,
    )

    # System Diagnostics singleton
    system_diagnostics = providers.Singleton(
        SystemDiagnostics,
        performance_monitor=performance_monitor,
        service_manager=service_manager,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )

    # Plugin Validator singleton
    plugin_validator = providers.Singleton(
        PluginValidator,
    )

    # Plugin Registry singleton
    plugin_registry = providers.Singleton(
        PluginRegistry,
    )

    # Plugin Loader singleton
    plugin_loader = providers.Singleton(
        PluginLoader,
        registry=plugin_registry,
        validator=plugin_validator,
    )

    # Audio Engine Subsystem singletons
    audio_device_manager = providers.Singleton(
        AudioDeviceManager,
    )

    audio_metrics = providers.Singleton(
        AudioMetrics,
    )

    audio_diagnostics = providers.Singleton(
        AudioDiagnostics,
        metrics=audio_metrics,
    )

    audio_engine = providers.Singleton(
        AudioEngine,
        config_manager=config_manager,
        device_manager=audio_device_manager,
        event_bus=event_bus,
        metrics=audio_metrics,
        diagnostics=audio_diagnostics,
    )

    # Clap Detection Subsystem singletons
    clap_metrics = providers.Singleton(
        ClapMetrics,
    )

    clap_diagnostics = providers.Singleton(
        ClapDiagnostics,
        metrics=clap_metrics,
    )

    clap_detector = providers.Singleton(
        ClapDetector,
        config_manager=config_manager,
        audio_engine=audio_engine,
        event_bus=event_bus,
        metrics=clap_metrics,
        diagnostics=clap_diagnostics,
    )

    # Wake Word Subsystem singletons
    wakeword_metrics = providers.Singleton(
        WakeWordMetrics,
    )

    wakeword_diagnostics = providers.Singleton(
        WakeWordDiagnostics,
        metrics=wakeword_metrics,
    )

    wakeword_model_provider = providers.Singleton(
        WakeWordModelProvider,
    )

    wakeword_detector = providers.Singleton(
        WakeWordDetector,
        config_manager=config_manager,
        audio_engine=audio_engine,
        event_bus=event_bus,
        model_provider=wakeword_model_provider,
        metrics=wakeword_metrics,
        diagnostics=wakeword_diagnostics,
    )

    # Voice Activity Detection (VAD) Subsystem singletons
    vad_metrics = providers.Singleton(
        VADMetrics,
    )

    silero_vad_model = providers.Singleton(
        SileroVADModel,
    )

    vad_detector = providers.Singleton(
        VADDetector,
        config_manager=config_manager,
        audio_engine=audio_engine,
        event_bus=event_bus,
        model=silero_vad_model,
        metrics=vad_metrics,
    )

    vad_diagnostics = providers.Singleton(
        VADDiagnostics,
        config=vad_detector.provided.vad_config,
        metrics=vad_metrics,
    )

    # Speech-to-Text (STT) Subsystem singletons
    stt_metrics = providers.Singleton(
        STTMetrics,
    )

    faster_whisper_engine = providers.Singleton(
        FasterWhisperSTTEngine,
    )

    stt_service = providers.Singleton(
        STTService,
        config_manager=config_manager,
        audio_engine=audio_engine,
        event_bus=event_bus,
        engine=faster_whisper_engine,
        metrics=stt_metrics,
    )

    stt_diagnostics = providers.Singleton(
        STTDiagnostics,
        metrics=stt_metrics,
    )

    # Text-to-Speech (TTS) Subsystem singletons
    tts_metrics = providers.Singleton(
        TTSMetrics,
    )

    piper_tts_provider = providers.Singleton(
        PiperTTSProvider,
    )

    tts_service = providers.Singleton(
        TTSService,
        config_manager=config_manager,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=piper_tts_provider,
        metrics=tts_metrics,
    )

    tts_diagnostics = providers.Singleton(
        TTSDiagnostics,
        metrics=tts_metrics,
    )

    # Conversation State Machine Subsystem singletons
    conversation_metrics = providers.Singleton(
        ConversationMetrics,
    )

    test_response_provider = providers.Singleton(
        TestResponseProvider,
    )

    conversation_state_machine = providers.Singleton(
        ConversationStateMachine,
        config_manager=config_manager,
        event_bus=event_bus,
        stt_service=stt_service,
        tts_service=tts_service,
        response_provider=test_response_provider,
        metrics=conversation_metrics,
    )

    conversation_diagnostics = providers.Singleton(
        ConversationDiagnostics,
        metrics=conversation_metrics,
    )

    # Conversation Manager Subsystem singletons
    conversation_manager_metrics = providers.Singleton(
        ConversationManagerMetrics,
    )

    reference_resolver = providers.Singleton(
        DeterministicReferenceResolver,
    )

    context_builder = providers.Singleton(
        ContextBuilder,
    )

    conversation_store = providers.Singleton(
        InMemConversationStore,
    )

    conversation_manager = providers.Singleton(
        ConversationManager,
        config_manager=config_manager,
        event_bus=event_bus,
        store=conversation_store,
        resolver=reference_resolver,
        context_builder=context_builder,
        metrics=conversation_manager_metrics,
    )

    manager_response_provider = providers.Singleton(
        ManagerResponseProvider,
        manager=conversation_manager,
    )

    conversation_manager_diagnostics = providers.Singleton(
        ConversationManagerDiagnostics,
        metrics=conversation_manager_metrics,
    )

    # Natural Greetings Subsystem singletons
    greeting_metrics = providers.Singleton(
        GreetingMetrics,
    )

    greeting_selector = providers.Singleton(
        GreetingSelector,
    )

    template_greeting_provider = providers.Singleton(
        TemplateGreetingProvider,
        selector=greeting_selector,
    )

    greeting_context_builder = providers.Singleton(
        GreetingContextBuilder,
        conversation_manager=conversation_manager,
    )

    # Local LLM Subsystem singletons
    llm_metrics = providers.Singleton(
        LLMMetrics,
    )

    llama_cpp_provider = providers.Singleton(
        LlamaCppProvider,
    )

    ollama_provider = providers.Singleton(
        OllamaProvider,
    )

    fake_ai_provider = providers.Singleton(
        FakeAIModelProvider,
    )

    llm_model_manager = providers.Singleton(
        LLMModelManager,
        config_manager=config_manager,
        event_bus=event_bus,
    )

    llm_diagnostics = providers.Singleton(
        LLMDiagnostics,
        metrics=llm_metrics,
    )

    # Tool Calling Engine Subsystem singletons
    tool_schema_registry = providers.Singleton(
        ToolSchemaRegistry,
        tool_registry=tool_registry,
    )

    tool_call_adapter = providers.Singleton(
        DefaultToolCallAdapter,
    )

    tool_calling_metrics = providers.Singleton(
        ToolCallingMetrics,
    )

    tool_calling_engine = providers.Singleton(
        ToolCallingEngine,
        config_manager=config_manager,
        event_bus=event_bus,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        schema_registry=tool_schema_registry,
        adapter=tool_call_adapter,
        metrics=tool_calling_metrics,
    )

    tool_calling_diagnostics = providers.Singleton(
        ToolCallingDiagnostics,
        metrics=tool_calling_metrics,
    )

    # Personality Engine Subsystem singletons
    emotional_classifier = providers.Singleton(
        EmotionalSignalClassifier,
    )

    behavioral_rules_engine = providers.Singleton(
        BehavioralRulesEngine,
    )

    personality_metrics = providers.Singleton(
        PersonalityMetrics,
    )

    personality_engine = providers.Singleton(
        PersonalityEngine,
        config_manager=config_manager,
        event_bus=event_bus,
        classifier=emotional_classifier,
        rules_engine=behavioral_rules_engine,
        metrics=personality_metrics,
    )

    personality_diagnostics = providers.Singleton(
        PersonalityDiagnostics,
        metrics=personality_metrics,
    )

    # Dynamic Response Generation Engine Subsystem singletons
    response_context_builder = providers.Singleton(
        ResponseContextBuilder,
    )

    response_strategy_selector = providers.Singleton(
        ResponseStrategySelector,
    )

    response_validator_normalizer = providers.Singleton(
        ResponseValidatorNormalizer,
    )

    response_metrics = providers.Singleton(
        ResponseGenerationMetrics,
    )

    response_generator = providers.Singleton(
        ResponseGenerator,
        config_manager=config_manager,
        event_bus=event_bus,
        llm_manager=llm_model_manager,
        context_builder=response_context_builder,
        strategy_selector=response_strategy_selector,
        validator_normalizer=response_validator_normalizer,
        metrics=response_metrics,
    )

    response_diagnostics = providers.Singleton(
        ResponseGenerationDiagnostics,
        metrics=response_metrics,
    )

    ai_greeting_provider = providers.Singleton(
        AIGreetingProvider,
        config_manager=config_manager,
        event_bus=event_bus,
        llm_manager=llm_model_manager,
        personality_engine=personality_engine,
        validator_normalizer=response_validator_normalizer,
        template_fallback_provider=template_greeting_provider,
        metrics=greeting_metrics,
    )

    greeting_service = providers.Singleton(
        GreetingService,
        config_manager=config_manager,
        event_bus=event_bus,
        conversation_manager=conversation_manager,
        tts_service=tts_service,
        provider=ai_greeting_provider,
        context_builder=greeting_context_builder,
        metrics=greeting_metrics,
    )

    greeting_diagnostics = providers.Singleton(
        GreetingDiagnostics,
        metrics=greeting_metrics,
    )

    # AI Orchestrator Subsystem singletons
    orchestrator_metrics = providers.Singleton(
        OrchestratorMetrics,
    )

    ai_orchestrator = providers.Singleton(
        AIOrchestrator,
        config_manager=config_manager,
        event_bus=event_bus,
        llm_manager=llm_model_manager,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
        personality_engine=personality_engine,
        response_generator=response_generator,
        conversation_manager=conversation_manager,
        metrics=orchestrator_metrics,
    )

    orchestrator_diagnostics = providers.Singleton(
        OrchestratorDiagnostics,
        metrics=orchestrator_metrics,
    )

    # OrchestratingResponseProvider bridges voice transcripts to the AI pipeline.
    # It replaces TestResponseProvider as the active response provider for the
    # ConversationStateMachine, enabling real tool execution from voice commands.
    # Defined here (after ai_orchestrator) to resolve declaration ordering.
    orchestrating_response_provider = providers.Singleton(
        OrchestratingResponseProvider,
        ai_orchestrator=ai_orchestrator,
    )

    # Phase 5.1 Short-Term Memory Subsystem singletons
    short_term_memory_store = providers.Singleton(
        ShortTermMemoryStore,
    )

    memory_metrics = providers.Singleton(
        MemoryMetrics,
    )

    short_term_memory_service = providers.Singleton(
        ShortTermMemoryService,
        store=short_term_memory_store,
    )

    memory_diagnostics = providers.Singleton(
        MemoryDiagnostics,
        service=short_term_memory_service,
        metrics=memory_metrics,
    )

    # Phase 5.2 Session Memory Subsystem singletons
    session_memory_metrics = providers.Singleton(
        SessionMemoryMetrics,
    )

    session_memory_service = providers.Singleton(
        SessionMemoryService,
        short_term_service=short_term_memory_service,
    )

    session_memory_diagnostics = providers.Singleton(
        SessionMemoryDiagnostics,
        service=session_memory_service,
        metrics=session_memory_metrics,
    )

    # Phase 5.3 Long-Term Memory Subsystem singletons
    memory_db_manager = providers.Singleton(
        MemoryDatabaseManager,
        config_manager=config_manager,
    )

    memory_repository = providers.Singleton(
        SQLAlchemyMemoryRepository,
        db_manager=memory_db_manager,
    )

    memory_promotion_service = providers.Singleton(
        MemoryPromotionService,
        repository=memory_repository,
    )

    long_term_memory_metrics = providers.Singleton(
        LongTermMemoryMetrics,
    )

    long_term_memory_service = providers.Singleton(
        LongTermMemoryService,
        repository=memory_repository,
        promotion_service=memory_promotion_service,
    )

    long_term_memory_diagnostics = providers.Singleton(
        LongTermMemoryDiagnostics,
        db_manager=memory_db_manager,
        service=long_term_memory_service,
        metrics=long_term_memory_metrics,
    )

    # Phase 5.4 User Profile Subsystem singletons
    user_profile_metrics = providers.Singleton(
        UserProfileMetrics,
    )

    user_profile_service = providers.Singleton(
        UserProfileService,
        long_term_service=long_term_memory_service,
    )

    user_profile_diagnostics = providers.Singleton(
        UserProfileDiagnostics,
        service=user_profile_service,
        metrics=user_profile_metrics,
    )

    # Phase 5.5 Semantic Memory & FAISS Vector Index Subsystem singletons
    embedding_provider = providers.Singleton(
        LocalEmbeddingProvider,
    )

    semantic_memory_text_builder = providers.Singleton(
        MemoryEmbeddingTextBuilder,
    )

    semantic_memory_index = providers.Singleton(
        FAISSMemoryIndex,
    )

    semantic_memory_metrics = providers.Singleton(
        SemanticMemoryMetrics,
    )

    semantic_memory_service = providers.Singleton(
        SemanticMemoryService,
        long_term_service=long_term_memory_service,
        db_manager=memory_db_manager,
        embedding_provider=embedding_provider,
        semantic_index=semantic_memory_index,
        text_builder=semantic_memory_text_builder,
        metrics=semantic_memory_metrics,
    )

    semantic_memory_diagnostics = providers.Singleton(
        SemanticMemoryDiagnostics,
        service=semantic_memory_service,
        metrics=semantic_memory_metrics,
    )

    # Phase 5.6 Memory Retrieval Subsystem singletons
    memory_retrieval_policy = providers.Singleton(
        MemoryRetrievalPolicy,
    )

    memory_query_builder = providers.Singleton(
        MemoryQueryBuilder,
    )

    memory_ranking_service = providers.Singleton(
        MemoryRankingService,
    )

    memory_context_builder = providers.Singleton(
        MemoryContextBuilder,
    )

    memory_retrieval_metrics = providers.Singleton(
        MemoryRetrievalMetrics,
    )

    memory_retrieval_service = providers.Singleton(
        MemoryRetrievalService,
        long_term_service=long_term_memory_service,
        user_profile_service=user_profile_service,
        session_service=session_memory_service,
        semantic_service=semantic_memory_service,
        policy=memory_retrieval_policy,
        query_builder=memory_query_builder,
        ranking_service=memory_ranking_service,
        context_builder=memory_context_builder,
        metrics=memory_retrieval_metrics,
    )

    memory_retrieval_diagnostics = providers.Singleton(
        MemoryRetrievalDiagnostics,
        service=memory_retrieval_service,
        metrics=memory_retrieval_metrics,
    )

    # Phase 5.7 Memory Privacy Governance singletons
    memory_privacy_policy = providers.Singleton(
        MemoryPrivacyPolicy,
    )

    memory_retention_service = providers.Singleton(
        MemoryRetentionService,
        long_term_service=long_term_memory_service,
        user_profile_service=user_profile_service,
        semantic_service=semantic_memory_service,
    )

    memory_privacy_metrics = providers.Singleton(
        MemoryPrivacyMetrics,
    )

    memory_privacy_service = providers.Singleton(
        MemoryPrivacyService,
        policy=memory_privacy_policy,
        retention_service=memory_retention_service,
        metrics=memory_privacy_metrics,
        long_term_service=long_term_memory_service,
        user_profile_service=user_profile_service,
        semantic_service=semantic_memory_service,
    )

    memory_privacy_diagnostics = providers.Singleton(
        MemoryPrivacyDiagnostics,
        service=memory_privacy_service,
        metrics=memory_privacy_metrics,
    )

    # Theme Manager singleton
    theme_manager = providers.Singleton(
        ThemeManager,
        config_manager=config_manager,
    )

    # Asset Manager singleton
    asset_manager = providers.Singleton(
        AssetManager,
    )

    # Window Manager singleton
    window_manager = providers.Singleton(
        WindowManager,
    )

    # Navigation Manager singleton
    navigation_manager = providers.Singleton(
        NavigationManager,
    )

    # UI State Manager singleton
    ui_state_manager = providers.Singleton(
        UIStateManager,
    )

    # System Tray Manager singleton
    tray_manager = providers.Singleton(
        TrayManager,
        app_name=providers.Callable(lambda s: s.app.name, s=settings),
        asset_manager=asset_manager,
    )

    # Notification Manager singleton
    notification_manager = providers.Singleton(
        NotificationManager,
        tray_manager=tray_manager,
        event_bus=event_bus,
    )

    # Phase 6.1 UI Automation Foundation singletons
    window_resolver = providers.Singleton(
        WindowResolver,
    )

    ui_automation_metrics = providers.Singleton(
        UIAutomationMetrics,
    )

    ui_tree_walker = providers.Singleton(
        UITreeWalker,
        max_depth=providers.Callable(
            lambda s: s.automation.uia.max_tree_depth, s=settings
        ),
        max_nodes=providers.Callable(
            lambda s: s.automation.uia.max_tree_nodes, s=settings
        ),
        max_children_per_node=providers.Callable(
            lambda s: s.automation.uia.max_children, s=settings
        ),
        include_offscreen=providers.Callable(
            lambda s: s.automation.uia.include_offscreen, s=settings
        ),
        include_disabled=providers.Callable(
            lambda s: s.automation.uia.include_disabled, s=settings
        ),
        sanitize_sensitive=providers.Callable(
            lambda s: s.automation.uia.diagnostic_redaction, s=settings
        ),
    )

    ui_element_finder = providers.Singleton(
        ElementFinder,
        tree_walker=ui_tree_walker,
        default_match_mode=providers.Callable(
            lambda s: MatchMode(s.automation.uia.default_match_mode), s=settings
        ),
    )

    ui_automation_diagnostics = providers.Singleton(
        UIAutomationDiagnostics,
        window_resolver=window_resolver,
        metrics=ui_automation_metrics,
    )

    ui_automation_engine = providers.Singleton(
        UIAutomationEngine,
        window_resolver=window_resolver,
        tree_walker=ui_tree_walker,
        element_finder=ui_element_finder,
        metrics=ui_automation_metrics,
        diagnostics=ui_automation_diagnostics,
    )

    native_input_backend = providers.Singleton(NativeInputBackend)
    pyautogui_input_backend = providers.Singleton(PyAutoGUIInputBackend)
    input_target_resolver = providers.Singleton(
        TargetResolver,
        bounds_check_enabled=settings.provided.automation.input.coordinate_bounds_check,
    )
    input_metrics = providers.Singleton(InputMetrics)
    input_failsafe = providers.Singleton(
        InputFailsafe,
        enabled=settings.provided.automation.input.failsafe_enabled,
    )
    input_interruption_monitor = providers.Singleton(
        InterruptionMonitor,
        enabled=settings.provided.automation.input.interruption_detection_enabled,
    )
    input_diagnostics = providers.Singleton(
        InputDiagnostics,
        native_backend=native_input_backend,
        pyautogui_backend=pyautogui_input_backend,
        failsafe=input_failsafe,
        interruption_monitor=input_interruption_monitor,
    )
    input_engine = providers.Singleton(
        InputEngine,
        native_backend=native_input_backend,
        pyautogui_backend=pyautogui_input_backend,
        target_resolver=input_target_resolver,
        failsafe=input_failsafe,
        interruption_monitor=input_interruption_monitor,
        metrics=input_metrics,
        diagnostics=input_diagnostics,
    )

    desktop_monitor_manager = providers.Singleton(MonitorManager)
    desktop_virtual_desktop_manager = providers.Singleton(VirtualDesktopManager)
    desktop_window_controller = providers.Singleton(
        WindowController,
        window_resolver=window_resolver,
        monitor_manager=desktop_monitor_manager,
    )
    desktop_workspace_manager = providers.Singleton(
        WorkspaceManager,
        window_controller=desktop_window_controller,
        monitor_manager=desktop_monitor_manager,
    )
    desktop_screen_capturer = providers.Singleton(
        ScreenCapturer,
        monitor_manager=desktop_monitor_manager,
    )
    desktop_clipboard_manager = providers.Singleton(
        ClipboardManager,
        max_text_chars=settings.provided.automation.desktop.clipboard_max_text_chars,
    )
    desktop_metrics = providers.Singleton(DesktopMetrics)
    desktop_diagnostics = providers.Singleton(
        DesktopDiagnostics,
        window_controller=desktop_window_controller,
        monitor_manager=desktop_monitor_manager,
        virtual_desktop_manager=desktop_virtual_desktop_manager,
        screen_capturer=desktop_screen_capturer,
        clipboard_manager=desktop_clipboard_manager,
    )
    desktop_controller = providers.Singleton(
        DesktopController,
        window_controller=desktop_window_controller,
        monitor_manager=desktop_monitor_manager,
        virtual_desktop_manager=desktop_virtual_desktop_manager,
        workspace_manager=desktop_workspace_manager,
        screen_capturer=desktop_screen_capturer,
        clipboard_manager=desktop_clipboard_manager,
        metrics=desktop_metrics,
        diagnostics=desktop_diagnostics,
    )

    # Phase 6.4 Application Control & Interaction Adapters singletons
    app_adapter_registry = providers.Singleton(ApplicationAdapterRegistry)
    app_launcher = providers.Singleton(
        ApplicationLauncher,
        window_resolver=window_resolver,
        window_controller=desktop_window_controller,
        path_security=path_security_manager,
    )
    explorer_adapter = providers.Singleton(
        ExplorerAdapter,
        window_resolver=window_resolver,
        window_controller=desktop_window_controller,
        uia_engine=ui_automation_engine,
        element_finder=ui_element_finder,
        input_engine=input_engine,
        filesystem_service=filesystem_service,
        launcher=app_launcher,
        path_security=path_security_manager,
    )
    terminal_adapter = providers.Singleton(
        TerminalAdapter,
        window_resolver=window_resolver,
        window_controller=desktop_window_controller,
        uia_engine=ui_automation_engine,
        element_finder=ui_element_finder,
        input_engine=input_engine,
        launcher=app_launcher,
        path_security=path_security_manager,
    )
    app_adapter_metrics = providers.Singleton(ApplicationAdapterMetrics)
    app_adapter_diagnostics = providers.Singleton(
        ApplicationAdapterDiagnostics,
        registry=app_adapter_registry,
        launcher=app_launcher,
        explorer_adapter=explorer_adapter,
        terminal_adapter=terminal_adapter,
    )
    app_adapter_manager = providers.Singleton(
        ApplicationAdapterManager,
        registry=app_adapter_registry,
        launcher=app_launcher,
        explorer_adapter=explorer_adapter,
        terminal_adapter=terminal_adapter,
        metrics=app_adapter_metrics,
        diagnostics=app_adapter_diagnostics,
    )

    # Phase 6.5 Multi-Step Automation Workflow Engine singletons
    workflow_action_registry = providers.Singleton(
        WorkflowActionRegistry,
        app_manager=app_adapter_manager,
        desktop_controller=desktop_controller,
        input_engine=input_engine,
        filesystem_service=filesystem_service,
    )
    workflow_verification_registry = providers.Singleton(VerificationRegistry)
    workflow_step_verifier = providers.Singleton(
        StepVerifier,
        registry=workflow_verification_registry,
        app_manager=app_adapter_manager,
        desktop_controller=desktop_controller,
        uia_engine=ui_automation_engine,
    )
    workflow_validator = providers.Singleton(
        WorkflowValidator,
        action_registry=workflow_action_registry,
        verifier_registry=workflow_verification_registry,
    )
    workflow_metrics = providers.Singleton(WorkflowMetrics)
    workflow_engine = providers.Singleton(
        WorkflowEngine,
        action_registry=workflow_action_registry,
        verifier_registry=workflow_verification_registry,
        validator=workflow_validator,
        step_verifier=workflow_step_verifier,
        input_engine=input_engine,
        event_bus=event_bus,
        metrics=workflow_metrics,
    )
    workflow_diagnostics = providers.Singleton(
        WorkflowDiagnostics,
        engine=workflow_engine,
        action_registry=workflow_action_registry,
        verifier_registry=workflow_verification_registry,
        metrics=workflow_metrics,
    )
    workflow_manager = providers.Singleton(
        WorkflowManager,
        app_manager=app_adapter_manager,
        desktop_controller=desktop_controller,
        input_engine=input_engine,
        filesystem_service=filesystem_service,
        event_bus=event_bus,
    )

    # Phase 6.6 Automation Tool Suite singletons
    uia_list_windows_tool = providers.Singleton(UiaListWindowsTool, desktop_controller=desktop_controller)
    uia_inspect_window_tool = providers.Singleton(UiaInspectWindowTool, desktop_controller=desktop_controller, uia_engine=ui_automation_engine)
    uia_find_element_tool = providers.Singleton(UiaFindElementTool, desktop_controller=desktop_controller, uia_engine=ui_automation_engine)

    input_mouse_click_tool = providers.Singleton(InputMouseClickTool, input_engine=input_engine)
    input_type_text_tool = providers.Singleton(InputTypeTextTool, input_engine=input_engine)
    input_press_hotkey_tool = providers.Singleton(InputPressHotkeyTool, input_engine=input_engine)

    window_list_open_tool = providers.Singleton(WindowListOpenTool, desktop_controller=desktop_controller)
    window_focus_tool = providers.Singleton(AutomationWindowFocusTool, desktop_controller=desktop_controller)
    window_maximize_tool = providers.Singleton(AutomationWindowMaximizeTool, desktop_controller=desktop_controller)
    window_snap_tool = providers.Singleton(WindowSnapTool, desktop_controller=desktop_controller)

    screen_capture_tool = providers.Singleton(ScreenCaptureTool, desktop_controller=desktop_controller)
    screen_list_monitors_tool = providers.Singleton(ScreenListMonitorsTool, desktop_controller=desktop_controller)

    clipboard_get_content_tool = providers.Singleton(ClipboardGetContentTool, desktop_controller=desktop_controller)
    clipboard_set_content_tool = providers.Singleton(ClipboardSetContentTool, desktop_controller=desktop_controller)

    application_launch_tool = providers.Singleton(ApplicationLaunchTool, app_manager=app_adapter_manager)
    application_attach_tool = providers.Singleton(ApplicationAttachTool, app_manager=app_adapter_manager)
    application_status_tool = providers.Singleton(AutomationApplicationStatusTool, app_manager=app_adapter_manager)

    explorer_navigate_tool = providers.Singleton(ExplorerNavigateTool, app_manager=app_adapter_manager)
    explorer_open_item_tool = providers.Singleton(ExplorerOpenItemTool, app_manager=app_adapter_manager)

    terminal_launch_tool = providers.Singleton(TerminalLaunchTool, app_manager=app_adapter_manager)
    terminal_read_output_tool = providers.Singleton(TerminalReadOutputTool, app_manager=app_adapter_manager)

    workflow_execute_sequence_tool = providers.Singleton(WorkflowExecuteSequenceTool, workflow_manager=workflow_manager)

    automation_tool_metrics = providers.Singleton(AutomationToolMetrics)
    automation_tool_diagnostics = providers.Singleton(
        AutomationToolDiagnostics,
        registry=tool_registry,
        metrics=automation_tool_metrics,
    )

    # Phase 6.7 Safety Governance singletons
    automation_safety_policy = providers.Singleton(AutomationSafetyPolicy)
    automation_safety_analyzer = providers.Singleton(
        AutomationSafetyAnalyzer,
        policy=automation_safety_policy,
        tool_registry=tool_registry,
    )
    automation_kill_switch = providers.Singleton(AutomationKillSwitch)
    automation_confirmation_manager = providers.Singleton(AutomationConfirmationManager)
    automation_audit_log = providers.Singleton(AutomationAuditLog)
    automation_safety_metrics = providers.Singleton(AutomationSafetyMetrics)
    automation_safety_diagnostics = providers.Singleton(
        AutomationSafetyDiagnostics,
        policy=automation_safety_policy,
        kill_switch=automation_kill_switch,
        registry=tool_registry,
        metrics=automation_safety_metrics,
    )
    automation_safety_manager = providers.Singleton(
        AutomationSafetyManager,
        policy=automation_safety_policy,
        analyzer=automation_safety_analyzer,
        kill_switch=automation_kill_switch,
        confirmation_manager=automation_confirmation_manager,
        audit_log=automation_audit_log,
        metrics=automation_safety_metrics,
        event_bus=event_bus,
        workflow_manager=workflow_manager,
    )
