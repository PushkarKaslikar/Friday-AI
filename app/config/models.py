"""Pydantic configuration models for application settings."""

from typing import Literal

from pydantic import BaseModel, Field


class AppInfoSettings(BaseModel):
    """Application core information settings."""

    name: str = Field(default="Friday AI Assistant", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment stage"
    )
    debug: bool = Field(default=True, description="Debug mode flag")


class UISettings(BaseModel):
    """User Interface settings."""

    theme: Literal["dark", "light", "system"] = Field(
        default="dark", description="Visual theme setting"
    )
    start_minimized: bool = Field(
        default=False, description="Whether to start minimized to system tray"
    )
    auto_start: bool = Field(
        default=False,
        description="Whether application launches automatically at Windows boot",
    )


class LoggingSettings(BaseModel):
    """Logging subsystem settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Minimum active log level"
    )
    log_to_console: bool = Field(default=True, description="Enable stdout log sink")
    log_to_file: bool = Field(default=True, description="Enable rotating file log sink")
    max_file_size_mb: int = Field(
        default=10, ge=1, le=100, description="Max individual log file size in MB"
    )
    retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to retain rotated log files",
    )


class AudioSettings(BaseModel):
    """Audio Engine Subsystem Settings."""

    enabled: bool = Field(default=True, description="Master audio engine enable flag")
    input_device_id: str | int | None = Field(
        default=None, description="Selected input device ID or stable identifier"
    )
    output_device_id: str | int | None = Field(
        default=None, description="Selected output device ID or stable identifier"
    )
    sample_rate: int = Field(
        default=16000,
        description="Default audio sample rate in Hz (16000Hz standard for AI/VAD/STT)",
    )
    input_channels: int = Field(
        default=1, description="Number of microphone input channels (1 = mono)"
    )
    output_channels: int = Field(
        default=2, description="Number of speaker output channels (2 = stereo)"
    )
    block_size: int = Field(
        default=512, description="Number of audio frames per callback block"
    )
    buffer_size_seconds: float = Field(
        default=5.0, description="Maximum ring buffer capacity in seconds"
    )
    dtype: str = Field(
        default="float32", description="Audio sample representation data type"
    )
    latency_mode: Literal["low", "high", "balanced"] = Field(
        default="low", description="Sounddevice stream latency mode target"
    )
    auto_fallback: bool = Field(
        default=True,
        description="Automatically fallback to system default device on disconnect",
    )


class ClapSettings(BaseModel):
    """Double-Clap Detection & Activation Subsystem Settings."""

    enabled: bool = Field(
        default=True, description="Enable double-clap gesture activation"
    )
    min_clap_interval_ms: int = Field(
        default=150,
        ge=50,
        le=500,
        description="Minimum allowed interval between two claps in ms",
    )
    max_clap_interval_ms: int = Field(
        default=1000,
        ge=300,
        le=3000,
        description="Maximum allowed interval between two claps in ms",
    )
    cooldown_ms: int = Field(
        default=2000,
        ge=500,
        le=10000,
        description="Refractory cooldown period after double clap in ms",
    )
    energy_threshold_multiplier: float = Field(
        default=4.5,
        ge=1.5,
        le=20.0,
        description="Energy multiplier threshold relative to noise floor",
    )
    min_peak_amplitude: float = Field(
        default=0.15,
        ge=0.01,
        le=0.9,
        description="Minimum peak amplitude threshold (0.0 to 1.0)",
    )
    min_duration_ms: float = Field(
        default=5.0, ge=1.0, le=30.0, description="Minimum impulse duration in ms"
    )
    max_duration_ms: float = Field(
        default=60.0, ge=10.0, le=200.0, description="Maximum impulse duration in ms"
    )
    confidence_threshold: float = Field(
        default=0.65,
        ge=0.1,
        le=1.0,
        description="Minimum confidence threshold for valid clap",
    )


class WakeWordSettings(BaseModel):
    """Wake Word Detection & Voice Activation Subsystem Settings."""

    enabled: bool = Field(
        default=True, description="Enable wake word detection activation"
    )
    model_name: str = Field(
        default="friday", description="Configured target wake word model identifier"
    )
    threshold: float = Field(
        default=0.70,
        ge=0.1,
        le=1.0,
        description="Minimum confidence score threshold for wake word detection",
    )
    cooldown_ms: int = Field(
        default=2000,
        ge=500,
        le=10000,
        description="Refractory cooldown period after wake word detection in ms",
    )
    custom_model_path: str | None = Field(
        default=None,
        description="Optional absolute path to custom .onnx wake word model",
    )


class VADSettings(BaseModel):
    """Voice Activity Detection (VAD) Subsystem Settings."""

    enabled: bool = Field(default=True, description="Enable voice activity detection")
    model_name: str = Field(
        default="silero_vad", description="VAD model name identifier"
    )
    speech_threshold: float = Field(
        default=0.50,
        ge=0.1,
        le=1.0,
        description="Speech probability threshold for candidate detection",
    )
    negative_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=0.9,
        description="Negative threshold for silence detection",
    )
    speech_start_confirmation_ms: float = Field(
        default=64.0,
        ge=10.0,
        le=1000.0,
        description="Duration required to confirm speech start in ms",
    )
    min_silence_duration_ms: float = Field(
        default=300.0,
        ge=50.0,
        le=3000.0,
        description="Minimum silence duration before confirming speech stop in ms",
    )
    speech_pad_ms: float = Field(
        default=64.0,
        ge=0.0,
        le=500.0,
        description="Speech padding duration in ms",
    )
    sample_rate: int = Field(
        default=16000,
        description="VAD expected audio sample rate in Hz",
    )
    custom_model_path: str | None = Field(
        default=None,
        description="Optional path to custom silero_vad.onnx model file",
    )


class STTSettings(BaseModel):
    """Configuration model for Speech-to-Text (STT) Subsystem."""

    enabled: bool = Field(default=True, description="Enable or disable STT subsystem")
    engine: str = Field(
        default="faster_whisper",
        description="Speech-to-text inference engine ('faster_whisper', 'parakeet')",
    )
    model_name: str = Field(
        default="base",
        description="Faster-Whisper or Parakeet model identifier ('tiny', 'base', 'small', 'medium', 'large-v3', 'turbo', 'nvidia/parakeet-tdt-0.6b-v3')",
    )
    device: str = Field(
        default="auto",
        description="Compute device execution target ('auto', 'cpu', 'cuda')",
    )
    compute_type: str = Field(
        default="auto",
        description="Model quantization compute type ('auto', 'int8', 'float16', 'float32')",
    )
    language: str | None = Field(
        default=None,
        description="Target transcription language code (None or 'auto' for auto-detect)",
    )
    beam_size: int = Field(default=5, ge=1, le=20, description="Beam search size")
    max_segment_duration_ms: float = Field(
        default=30000.0,
        ge=1000.0,
        le=120000.0,
        description="Maximum speech segment buffer duration in ms",
    )
    word_timestamps: bool = Field(
        default=False, description="Enable word-level timestamp generation"
    )
    vad_filter: bool = Field(
        default=False, description="Enable Whisper internal VAD filtering"
    )
    custom_model_path: str | None = Field(
        default=None,
        description="Optional path to custom Whisper model directory or file",
    )


class TTSSettings(BaseModel):
    """Configuration settings for Text-to-Speech (TTS) engine."""

    enabled: bool = Field(default=True, description="Enable or disable TTS engine")
    voice: str = Field(
        default="en_US-amy-medium", description="Selected Piper voice model name"
    )
    language: str = Field(default="en_US", description="Target language code")
    model_path: str | None = Field(
        default=None, description="Optional explicit path to Piper ONNX model"
    )
    config_path: str | None = Field(
        default=None, description="Optional explicit path to Piper model JSON config"
    )
    max_text_length: int = Field(
        default=500, description="Maximum sentence length before text chunking"
    )
    auto_play: bool = Field(
        default=True,
        description="Automatically play synthesized speech through speaker",
    )
    use_cuda: bool = Field(
        default=False, description="Enable CUDA acceleration for Piper model"
    )


class ConversationSettings(BaseModel):
    """Configuration settings for Conversation State Machine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Conversation State Machine"
    )
    session_timeout_seconds: float = Field(
        default=10.0, description="Idle conversation session timeout in seconds"
    )
    barge_in_enabled: bool = Field(
        default=True, description="Enable user barge-in speech interruption during TTS"
    )
    minimum_barge_in_duration_ms: float = Field(
        default=100.0, description="Minimum speech duration in ms to trigger barge-in"
    )


class ConversationManagerSettings(BaseModel):
    """Configuration settings for Conversation Manager & Conversational Continuity."""

    enabled: bool = Field(
        default=True, description="Enable or disable Conversation Manager"
    )
    max_turns: int = Field(
        default=20, description="Maximum historical turns to retain in context"
    )
    max_context_characters: int = Field(
        default=4000, description="Maximum total character budget for context snapshot"
    )
    max_context_tokens: int = Field(
        default=1000, description="Maximum estimated token limit for context window"
    )
    max_entities: int = Field(
        default=30, description="Maximum active tracked entities in memory"
    )
    max_tool_result_chars: int = Field(
        default=2000,
        description="Maximum characters per tool result payload in context",
    )
    pending_request_timeout_seconds: float = Field(
        default=60.0,
        description="Timeout limit in seconds for pending clarification requests",
    )
    context_compaction_enabled: bool = Field(
        default=True, description="Enable deterministic context compaction"
    )


class GreetingSettings(BaseModel):
    """Configuration settings for Natural Greetings Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable natural activation greetings"
    )
    max_recent_history: int = Field(
        default=5,
        description="Maximum recent greetings to retain for repetition prevention",
    )
    avoid_repetition: bool = Field(
        default=True,
        description="Avoid repeating identical greetings across consecutive activations",
    )
    default_style: str = Field(
        default="FRIDAY",
        description="Default greeting style profile (FRIDAY, PROFESSIONAL, etc.)",
    )
    use_context: bool = Field(
        default=True, description="Use context-aware greeting selection strategy"
    )
    ai_enabled: bool = Field(
        default=True, description="Enable AI-generated context-aware greetings"
    )
    ai_timeout_seconds: float = Field(
        default=3.0, description="Timeout limit in seconds for AI greeting generation"
    )
    provider: str = Field(
        default="ai", description="Greeting provider selection ('ai' or 'template')"
    )
    fallback_enabled: bool = Field(
        default=True,
        description="Fallback to deterministic template greeting on failure",
    )


class LlamaCppSettings(BaseModel):
    """Specific configuration settings for llama.cpp GGUF provider."""

    model_path: str = Field(
        default="models/llm/tinyllama-1.1b-chat.Q4_K_M.gguf",
        description="Path to local GGUF model file",
    )
    context_size: int = Field(default=4096, description="Context window size in tokens")
    gpu_layers: int = Field(
        default=0, description="Number of model layers to offload to GPU/CUDA"
    )
    threads: int = Field(default=4, description="Number of CPU threads for inference")
    batch_size: int = Field(default=512, description="Prompt processing batch size")


class OllamaSettings(BaseModel):
    """Specific configuration settings for Ollama REST provider boundary."""

    host: str = Field(
        default="http://localhost:11434", description="Local Ollama service URL"
    )
    model_name: str = Field(
        default="tinyllama", description="Ollama model identifier tag"
    )


class LLMSettings(BaseModel):
    """Root configuration settings for Local LLM Runtime."""

    provider: str = Field(
        default="llama_cpp",
        description="Active model provider (llama_cpp, ollama, fake)",
    )
    model_name: str = Field(
        default="tinyllama-1.1b-chat.Q4_K_M.gguf", description="Model identifier name"
    )
    model_path: str = Field(
        default="models/llm/tinyllama-1.1b-chat.Q4_K_M.gguf",
        description="Path to local GGUF model file",
    )
    preload_model: bool = Field(
        default=False,
        description="Preload model on application startup if True (lazy-load if False)",
    )
    context_size: int = Field(
        default=4096, description="Maximum context window size in tokens"
    )
    temperature: float = Field(
        default=0.7, description="Generation temperature sampling parameter"
    )
    top_p: float = Field(default=0.9, description="Nucleus top_p sampling parameter")
    top_k: int = Field(default=40, description="Top-k sampling parameter")
    max_tokens: int = Field(default=512, description="Maximum generated output tokens")
    use_cuda: bool = Field(
        default=False, description="Enable GPU/CUDA acceleration if available"
    )
    gpu_layers: int = Field(default=0, description="Number of GPU layers")
    threads: int = Field(default=4, description="CPU threads for generation")
    llama_cpp: LlamaCppSettings = Field(default_factory=LlamaCppSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)


class OrchestratorSettings(BaseModel):
    """Configuration settings for AI Orchestrator & Reasoning Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable AI Orchestrator workflow engine"
    )
    max_steps: int = Field(
        default=5, description="Maximum reasoning and tool execution loop steps"
    )
    allow_tools: bool = Field(
        default=True, description="Allow tool selection and execution in orchestration"
    )
    system_prompt_style: str = Field(
        default="DEFAULT", description="System prompt formatting style profile"
    )


class ToolCallingSettings(BaseModel):
    """Configuration settings for Tool Calling & Function Binding Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Tool Calling Engine"
    )
    max_tool_definitions: int = Field(
        default=20, description="Maximum tool schema definitions sent in model prompt"
    )
    max_result_chars: int = Field(
        default=4000,
        description="Maximum serialized result characters for model context",
    )
    duplicate_call_protection: bool = Field(
        default=True,
        description="Detect and handle duplicate tool calls within same workflow",
    )
    schema_cache_enabled: bool = Field(
        default=True,
        description="Enable thread-safe schema caching for registered tools",
    )


class FridayPersonalitySettings(BaseModel):
    """Configuration settings for Personality Engine & Behavioral Identity System."""

    enabled: bool = Field(
        default=True, description="Enable or disable Personality Engine"
    )
    name: str = Field(default="Friday", description="Assistant identity name")
    role: str = Field(
        default="Personal AI Assistant", description="Assistant role description"
    )
    formality: float = Field(
        default=0.5,
        description="Communication formality scale (0.0=Casual to 1.0=Formal)",
    )
    humor: float = Field(
        default=0.25, description="Humor frequency scale (0.0=None to 1.0=Frequent)"
    )
    emotional_responsiveness: float = Field(
        default=0.7,
        description="Emotional responsiveness scale (0.0=Robot to 1.0=Empathetic)",
    )
    proactivity: float = Field(
        default=0.4, description="Proactivity scale (0.0=Reactive to 1.0=Proactive)"
    )
    conciseness: float = Field(
        default=0.75, description="Conciseness scale (0.0=Verbose to 1.0=Concise)"
    )
    preferred_name: str | None = Field(
        default=None, description="Preferred name to address user"
    )
    address_style: str = Field(
        default="natural", description="Address style preference"
    )


class ResponseGenerationSettings(BaseModel):
    """Configuration settings for Dynamic Response Generation Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Dynamic Response Generator"
    )
    max_response_chars: int = Field(
        default=2000, description="Maximum character limit for generated responses"
    )
    max_response_tokens: int = Field(
        default=512, description="Maximum token limit for generated responses"
    )
    temperature: float = Field(
        default=0.3, description="LLM sampling temperature for response generation"
    )
    streaming_enabled: bool = Field(
        default=True, description="Enable iterative token streaming when supported"
    )
    timeout_seconds: float = Field(
        default=10.0, description="Response generation timeout limit in seconds"
    )
    default_mode: str = Field(
        default="NORMAL", description="Default response generation mode"
    )


class ShortTermMemorySettings(BaseModel):
    """Configuration settings for Phase 5.1 Short-Term Memory Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Short-Term Memory subsystem"
    )
    max_entries: int = Field(
        default=100, description="Maximum stored memory entries per session"
    )
    max_turns: int = Field(
        default=20, description="Maximum conversation turns preserved in context"
    )
    max_entities: int = Field(
        default=30, description="Maximum active entities retained in memory"
    )
    max_context_characters: int = Field(
        default=4000, description="Maximum character budget for memory snapshots"
    )
    max_tool_result_characters: int = Field(
        default=2000, description="Maximum character size for individual tool results"
    )
    max_entry_size: int = Field(
        default=1000, description="Maximum character size for individual turn texts"
    )
    eviction_policy: str = Field(
        default="RECENCY_PRIORITY", description="Eviction policy for bounded memory"
    )


class SessionMemorySettings(BaseModel):
    """Configuration settings for Phase 5.2 Session Memory Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Session Memory subsystem"
    )
    max_tasks: int = Field(
        default=10, description="Maximum session tasks retained in memory"
    )
    max_topics: int = Field(
        default=10, description="Maximum bounded topic history preserved in session"
    )
    max_workflows: int = Field(
        default=10, description="Maximum workflow execution records per session"
    )
    max_entities: int = Field(
        default=30, description="Maximum active session entities retained"
    )
    max_snapshot_characters: int = Field(
        default=4000, description="Maximum character budget for session snapshots"
    )
    max_session_preferences: int = Field(
        default=20, description="Maximum temporary session-only preferences"
    )


class LongTermMemorySettings(BaseModel):
    """Configuration settings for Phase 5.3 Long-Term Persistent Memory Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Long-Term Memory subsystem"
    )
    db_path: str = Field(
        default="", description="Configurable path to SQLite memory database file"
    )
    max_total_memories: int = Field(
        default=1000, description="Maximum total active persistent long-term memories"
    )
    max_content_chars: int = Field(
        default=1000, description="Maximum character budget for memory text"
    )
    max_metadata_chars: int = Field(
        default=2000, description="Maximum character budget for metadata"
    )


class UserProfileSettings(BaseModel):
    """Configuration settings for Phase 5.4 User Profile Domain Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable User Profile subsystem"
    )
    max_projects: int = Field(
        default=20, description="Maximum active project profiles retained"
    )
    max_contacts: int = Field(
        default=50, description="Maximum explicitly remembered contact profiles"
    )
    max_workflows: int = Field(
        default=20, description="Maximum workflow profiles retained"
    )
    max_snapshot_chars: int = Field(
        default=4000,
        description="Maximum character budget for profile prompt snapshots",
    )


class SemanticMemorySettings(BaseModel):
    """Configuration settings for Phase 5.5 Semantic Memory & FAISS Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable Semantic Memory subsystem"
    )
    embedding_provider: str = Field(
        default="local", description="Embedding provider type (e.g. 'local')"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Local embedding model identifier"
    )
    device: str = Field(
        default="AUTO", description="Execution device (CPU, CUDA, AUTO)"
    )
    batch_size: int = Field(
        default=32, description="Batch size for vector embedding generation"
    )
    normalize_embeddings: bool = Field(
        default=True, description="Enable L2 vector normalization"
    )
    top_k: int = Field(
        default=10, description="Default top-k nearest neighbor vector results"
    )
    index_path: str = Field(
        default="", description="Configurable path to FAISS vector index file"
    )
    index_version: int = Field(default=1, description="Semantic index schema version")
    auto_sync: bool = Field(
        default=True, description="Enable automatic incremental synchronization"
    )
    max_memory_text_chars: int = Field(
        default=1000, description="Maximum character budget for embedding text"
    )


class MemoryRetrievalSettings(BaseModel):
    """Configuration settings for Phase 5.6 Memory Retrieval Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable Memory Retrieval subsystem"
    )
    auto_trigger: bool = Field(
        default=True, description="Enable automatic policy-based retrieval triggering"
    )
    max_candidates: int = Field(
        default=15, description="Maximum initial candidate memories fetched"
    )
    max_results: int = Field(
        default=5, description="Maximum ranked candidate memories selected"
    )
    similarity_threshold: float = Field(
        default=0.35, ge=0.0, le=1.0, description="Minimum relevance score threshold"
    )
    max_context_characters: int = Field(
        default=1500, description="Maximum prompt context character budget"
    )
    max_context_memories: int = Field(
        default=5, description="Maximum memories included in prompt context"
    )
    semantic_weight: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Ranking weight for semantic similarity",
    )
    recency_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Ranking weight for memory recency"
    )
    importance_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Ranking weight for memory importance"
    )
    confidence_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Ranking weight for memory confidence"
    )
    source_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Ranking weight for source trust"
    )
    context_match_weight: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Ranking weight for context match"
    )
    session_priority: bool = Field(
        default=True, description="Enable current session context precedence"
    )
    profile_priority: bool = Field(
        default=True, description="Enable UserProfile context precedence"
    )


class MemoryPrivacySettings(BaseModel):
    """Configuration settings for Phase 5.7 Memory Privacy Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable Memory Privacy subsystem"
    )
    mode: str = Field(
        default="NORMAL",
        description="Operational privacy mode (NORMAL, STRICT, NO_PERSISTENCE)",
    )
    allow_persistent_memory: bool = Field(
        default=True,
        description="Enable or disable persistent long-term memory creation",
    )
    require_confirmation_for_personal: bool = Field(
        default=False,
        description="Require user confirmation for personal/sensitive memories",
    )
    allow_semantic_indexing: bool = Field(
        default=True, description="Enable or disable semantic FAISS vector indexing"
    )
    allow_sensitive_retrieval: bool = Field(
        default=True, description="Allow sensitive memory retrieval under policy"
    )
    default_retention: str = Field(
        default="PERSISTENT", description="Default memory retention category"
    )
    auto_cleanup: bool = Field(
        default=True, description="Enable automatic background retention cleanup"
    )
    audit_enabled: bool = Field(
        default=True, description="Enable privacy audit event logging"
    )


class UIAutomationSettings(BaseModel):
    """Configuration settings for Phase 6.1 UI Automation Foundation Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable UI Automation engine"
    )
    max_tree_depth: int = Field(
        default=10, ge=1, le=50, description="Maximum UI tree traversal depth limit"
    )
    max_tree_nodes: int = Field(
        default=500, ge=10, le=5000, description="Maximum UI tree node traversal cap"
    )
    max_children: int = Field(
        default=50, ge=5, le=500, description="Maximum direct children per node cap"
    )
    default_match_mode: str = Field(
        default="EXACT",
        description="Default locator string match mode (EXACT, CASE_INSENSITIVE, CONTAINS, STARTS_WITH)",
    )
    include_offscreen: bool = Field(
        default=False,
        description="Whether to include offscreen UI elements in tree search by default",
    )
    include_disabled: bool = Field(
        default=False,
        description="Whether to include disabled UI elements in tree search by default",
    )
    diagnostic_redaction: bool = Field(
        default=True,
        description="Enable automatic password field and secret UI data redaction",
    )


class AutomationInputSettings(BaseModel):
    """Configuration settings for Phase 6.2 Mouse, Keyboard & Human-Like Input Subsystem."""

    enabled: bool = Field(
        default=True, description="Enable or disable input control engine"
    )
    default_backend: str = Field(
        default="NATIVE", description="Default input backend (NATIVE, PYAUTOGUI)"
    )
    failsafe_enabled: bool = Field(
        default=True, description="Enable top-left corner emergency mouse failsafe"
    )
    interruption_detection_enabled: bool = Field(
        default=True,
        description="Enable real-time physical user input override detection",
    )
    mouse_move_duration: float = Field(
        default=0.2,
        ge=0.0,
        le=10.0,
        description="Default mouse movement duration in seconds",
    )
    click_interval_ms: int = Field(
        default=100,
        ge=0,
        le=5000,
        description="Default mouse click interval in milliseconds",
    )
    typing_profile: str = Field(
        default="NORMAL",
        description="Default typing speed profile (INSTANT, FAST, NORMAL, SLOW)",
    )
    typing_interval_ms: int = Field(
        default=50,
        ge=0,
        le=5000,
        description="Default inter-character typing delay in milliseconds",
    )
    operation_timeout_ms: int = Field(
        default=10000,
        ge=1000,
        le=60000,
        description="Maximum operation timeout in milliseconds",
    )
    max_sequence_actions: int = Field(
        default=50, ge=1, le=500, description="Maximum input sequence action cap"
    )
    coordinate_bounds_check: bool = Field(
        default=True, description="Enable virtual screen coordinate bounds checking"
    )


class AutomationDesktopSettings(BaseModel):
    """Phase 6.3 Window Management, Desktop Control, Clipboard & Screen Inspection Settings."""

    enabled: bool = Field(
        default=True, description="Enable or disable desktop control subsystem"
    )
    max_windows: int = Field(
        default=100, ge=1, le=1000, description="Maximum window count limit"
    )
    max_monitors: int = Field(
        default=10, ge=1, le=64, description="Maximum monitor count limit"
    )
    max_workspace_windows: int = Field(
        default=50, ge=1, le=500, description="Maximum workspace layout window cap"
    )
    window_operation_timeout_ms: int = Field(
        default=5000, ge=500, le=60000, description="Window operation timeout in ms"
    )
    screenshot_timeout_ms: int = Field(
        default=3000, ge=500, le=30000, description="Screenshot capture timeout in ms"
    )
    clipboard_timeout_ms: int = Field(
        default=2000, ge=200, le=10000, description="Clipboard operation timeout in ms"
    )
    clipboard_max_text_chars: int = Field(
        default=100000,
        ge=1000,
        le=1000000,
        description="Clipboard max text character limit",
    )
    screen_capture_enabled: bool = Field(
        default=True, description="Enable or disable local screen capture"
    )
    workspace_enabled: bool = Field(
        default=True, description="Enable or disable workspace layout capture/restore"
    )
    clipboard_enabled: bool = Field(
        default=True, description="Enable or disable clipboard operations"
    )
    virtual_desktop_enabled: bool = Field(
        default=True, description="Enable or disable virtual desktop queries"
    )
    diagnostic_redaction: bool = Field(
        default=True, description="Mask sensitive information in diagnostic outputs"
    )


class AutomationAppsSettings(BaseModel):
    """Configuration settings for Phase 6.4 Application Control & Interaction Adapters."""

    enabled: bool = Field(
        default=True, description="Enable or disable Application Adapters subsystem"
    )
    launch_timeout_ms: int = Field(
        default=10000,
        ge=1000,
        le=60000,
        description="Default application launch timeout in ms",
    )
    attach_timeout_ms: int = Field(
        default=5000,
        ge=500,
        le=30000,
        description="Default application attach timeout in ms",
    )
    explorer_enabled: bool = Field(
        default=True, description="Enable or disable File Explorer adapter"
    )
    terminal_enabled: bool = Field(
        default=True, description="Enable or disable Terminal family adapter"
    )
    launcher_enabled: bool = Field(
        default=True, description="Enable or disable generic ApplicationLauncher"
    )
    preferred_terminal: str = Field(
        default="cmd", description="Preferred terminal type (cmd, powershell, wt)"
    )
    max_output_characters: int = Field(
        default=4096,
        ge=100,
        le=65536,
        description="Maximum terminal output buffer character limit",
    )
    max_explorer_items: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum visible Explorer items to inspect",
    )


class AutomationWorkflowSettings(BaseModel):
    """Configuration settings for Phase 6.5 Multi-Step Automation Workflow Engine."""

    enabled: bool = Field(
        default=True, description="Enable or disable Workflow Engine subsystem"
    )
    max_steps: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum allowed steps bound per workflow plan",
    )
    max_retries_per_step: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries per workflow step",
    )
    max_total_retries: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum total retries per workflow execution",
    )
    default_step_timeout_ms: int = Field(
        default=10000,
        ge=500,
        le=120000,
        description="Default step execution timeout in ms",
    )
    default_workflow_timeout_ms: int = Field(
        default=60000,
        ge=1000,
        le=600000,
        description="Default total workflow timeout in ms",
    )
    verification_poll_interval_ms: int = Field(
        default=250,
        ge=50,
        le=5000,
        description="Default verification polling interval in ms",
    )
    history_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="In-memory execution history snapshot limit",
    )
    default_mode: str = Field(
        default="SIMULATE",
        description="Default execution safety mode (DRY_RUN, SIMULATE, LIVE)",
    )
    parallelism_enabled: bool = Field(
        default=False,
        description="Enable or disable parallel workflow execution (Default: False)",
    )


class AutomationToolSettings(BaseModel):
    """Configuration settings for Phase 6.6 Automation Tool Suite."""

    enabled: bool = Field(
        default=True, description="Enable or disable Automation Tool Suite"
    )
    uia_tools_enabled: bool = Field(
        default=True, description="Enable or disable UIA inspection tools"
    )
    input_tools_enabled: bool = Field(
        default=True, description="Enable or disable Mouse & Keyboard input tools"
    )
    window_tools_enabled: bool = Field(
        default=True, description="Enable or disable Window control tools"
    )
    screen_tools_enabled: bool = Field(
        default=True, description="Enable or disable Screen capture tools"
    )
    clipboard_tools_enabled: bool = Field(
        default=True, description="Enable or disable Clipboard tools"
    )
    application_tools_enabled: bool = Field(
        default=True, description="Enable or disable Application control tools"
    )
    explorer_tools_enabled: bool = Field(
        default=True, description="Enable or disable File Explorer tools"
    )
    terminal_tools_enabled: bool = Field(
        default=True, description="Enable or disable Terminal tools"
    )
    workflow_tool_enabled: bool = Field(
        default=True, description="Enable or disable Workflow sequence execution tool"
    )


class AutomationSafetySettings(BaseModel):
    """Configuration settings for Phase 6.7 Safety & Governance."""

    enabled: bool = Field(
        default=True, description="Enable or disable Safety Governance subsystem"
    )
    mode: str = Field(
        default="NORMAL",
        description="Execution safety policy mode (NORMAL, STRICT, LOCKDOWN)",
    )
    require_confirmation_high: bool = Field(
        default=True,
        description="Require explicit user confirmation for HIGH risk actions",
    )
    require_confirmation_critical: bool = Field(
        default=True,
        description="Require explicit user confirmation for CRITICAL risk actions",
    )
    max_steps: int = Field(
        default=50, ge=1, le=100, description="Maximum steps blast radius bound"
    )
    max_duration_ms: int = Field(
        default=300000,
        ge=1000,
        le=600000,
        description="Maximum duration blast radius bound in ms",
    )
    max_blast_apps: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum target applications blast radius bound",
    )
    max_blast_files: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum target files blast radius bound",
    )
    max_actions_per_second: int = Field(
        default=10, ge=1, le=50, description="Maximum action rate limit per second"
    )
    max_workflows_per_minute: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Maximum workflow execution rate limit per minute",
    )
    kill_switch_enabled: bool = Field(
        default=True, description="Enable or disable global emergency kill switch"
    )
    user_interrupt_enabled: bool = Field(
        default=True,
        description="Enable or disable physical user interruption monitoring",
    )
    failsafe_required: bool = Field(
        default=True, description="Require top-left mouse failsafe corner protection"
    )
    audit_enabled: bool = Field(
        default=True, description="Enable or disable safety audit logging"
    )
    audit_history_size: int = Field(
        default=500,
        ge=50,
        le=5000,
        description="Maximum bounded audit history events",
    )
    lockdown_on_failure: bool = Field(
        default=False,
        description="Automatically transition to LOCKDOWN on safety dependency failure",
    )


class AutomationSettings(BaseModel):
    """Phase 6 Computer Automation Subsystem Settings."""

    uia: UIAutomationSettings = Field(default_factory=UIAutomationSettings)
    input: AutomationInputSettings = Field(default_factory=AutomationInputSettings)
    desktop: AutomationDesktopSettings = Field(
        default_factory=AutomationDesktopSettings
    )
    apps: AutomationAppsSettings = Field(default_factory=AutomationAppsSettings)
    workflow: AutomationWorkflowSettings = Field(
        default_factory=AutomationWorkflowSettings
    )
    tools: AutomationToolSettings = Field(
        default_factory=AutomationToolSettings
    )
    safety: AutomationSafetySettings = Field(
        default_factory=AutomationSafetySettings
    )


class Settings(BaseModel):
    """Root configuration object containing sub-configuration domain models."""

    app: AppInfoSettings = Field(default_factory=AppInfoSettings)
    ui: UISettings = Field(default_factory=UISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    clap: ClapSettings = Field(default_factory=ClapSettings)
    wake_word: WakeWordSettings = Field(default_factory=WakeWordSettings)
    vad: VADSettings = Field(default_factory=VADSettings)
    stt: STTSettings = Field(default_factory=STTSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    conversation_manager: ConversationManagerSettings = Field(
        default_factory=ConversationManagerSettings
    )
    greeting: GreetingSettings = Field(default_factory=GreetingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)
    tool_calling: ToolCallingSettings = Field(default_factory=ToolCallingSettings)
    friday: FridayPersonalitySettings = Field(default_factory=FridayPersonalitySettings)
    response_generation: ResponseGenerationSettings = Field(
        default_factory=ResponseGenerationSettings
    )
    short_term_memory: ShortTermMemorySettings = Field(
        default_factory=ShortTermMemorySettings
    )
    session_memory: SessionMemorySettings = Field(default_factory=SessionMemorySettings)
    long_term_memory: LongTermMemorySettings = Field(
        default_factory=LongTermMemorySettings
    )
    user_profile: UserProfileSettings = Field(default_factory=UserProfileSettings)
    semantic_memory: SemanticMemorySettings = Field(
        default_factory=SemanticMemorySettings
    )
    memory_retrieval: MemoryRetrievalSettings = Field(
        default_factory=MemoryRetrievalSettings
    )
    memory_privacy: MemoryPrivacySettings = Field(default_factory=MemoryPrivacySettings)
    automation: AutomationSettings = Field(default_factory=AutomationSettings)
