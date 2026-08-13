"""Central Conversation Manager & Short-Term Memory Orchestrator.

Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

import re
import threading
import time
from typing import Any

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.conversation.context_builder import ContextBuilder
from app.voice.conversation.conversation_manager_interface import IConversationManager
from app.voice.conversation.conversation_store import InMemConversationStore
from app.voice.conversation.events import (
    ConversationActivated,
    ConversationEnded,
    ConversationSpeakingCompleted,
    ConversationSpeakingStarted,
)
from app.voice.conversation.manager_diagnostics import ConversationManagerDiagnostics
from app.voice.conversation.manager_events import (
    ClarificationRequired,
    ClarificationResolved,
    ContextUpdated,
    ConversationSessionEnded,
    ConversationSessionStarted,
    ConversationTurnCompleted,
    ConversationTurnStarted,
    ReferenceAmbiguous,
    ReferenceResolved,
)
from app.voice.conversation.manager_metrics import ConversationManagerMetrics
from app.voice.conversation.manager_models import (
    ContextSnapshot,
    ConversationalStateCategory,
    ConversationManagerConfiguration,
    ConversationTurn,
    EntityCategory,
    PendingRequest,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    SpeakerRole,
    TrackedEntity,
)
from app.voice.conversation.reference_resolver import DeterministicReferenceResolver
from app.voice.conversation.response_provider_interface import (
    IConversationResponseProvider,
)
from app.voice.stt.events import TranscriptionCompleted


class ManagerResponseProvider(IConversationResponseProvider):
    """Bridge response provider exposing ConversationManager intelligence to ConversationStateMachine."""

    def __init__(self, manager: "ConversationManager") -> None:
        self.manager = manager

    def get_response(self, transcript: str, session_id: str = "") -> str:
        """Generate contextual response for user transcript."""
        return self.manager.generate_contextual_response(transcript, session_id)


class ConversationManager(BaseService, IConversationManager):
    """Central service managing short-term conversational context, entity tracking, and reference resolution."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        store: InMemConversationStore | None = None,
        resolver: DeterministicReferenceResolver | None = None,
        context_builder: ContextBuilder | None = None,
        metrics: ConversationManagerMetrics | None = None,
        diagnostics: ConversationManagerDiagnostics | None = None,
    ) -> None:
        super().__init__(name="ConversationManager", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.store = store or InMemConversationStore()
        self.resolver = resolver or DeterministicReferenceResolver()
        self.metrics = metrics or ConversationManagerMetrics()
        self.diagnostics = diagnostics or ConversationManagerDiagnostics(
            metrics=self.metrics
        )

        self._manager_config: ConversationManagerConfiguration = (
            self._load_manager_configuration()
        )
        self.context_builder = context_builder or ContextBuilder(
            config=self._manager_config
        )

        self._lock = threading.Lock()
        self._last_error: str | None = None
        self._active_session_id: str | None = None

    @property
    def manager_config(self) -> ConversationManagerConfiguration:
        """Active configuration model."""
        return self._manager_config

    def _load_manager_configuration(self) -> ConversationManagerConfiguration:
        """Load conversation manager settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "conversation_manager"):
                cfg = settings.conversation_manager
                return ConversationManagerConfiguration(
                    enabled=cfg.enabled,
                    max_turns=cfg.max_turns,
                    max_context_characters=cfg.max_context_characters,
                    max_context_tokens=cfg.max_context_tokens,
                    max_entities=cfg.max_entities,
                    pending_request_timeout_seconds=cfg.pending_request_timeout_seconds,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"ConversationManager: Failed to load settings, using defaults: {exc}"
            )

        return ConversationManagerConfiguration()

    def _do_initialize(self) -> None:
        """Initialize service parameters."""
        logger.info("ConversationManager: Service initialized.")

    def _do_start(self) -> None:
        """Subscribe to EventBus lifecycle and voice events."""
        self.event_bus.subscribe(ConversationActivated, self._on_conversation_activated)
        self.event_bus.subscribe(ConversationEnded, self._on_conversation_ended)
        self.event_bus.subscribe(
            TranscriptionCompleted, self._on_transcription_completed
        )
        self.event_bus.subscribe(ConversationSpeakingStarted, self._on_speaking_started)
        self.event_bus.subscribe(
            ConversationSpeakingCompleted, self._on_speaking_completed
        )
        logger.info("ConversationManager: Subscribed to EventBus events.")

    def _do_stop(self) -> None:
        """Stop service and flush in-memory store."""
        self.store.clear_all()
        logger.info(
            "ConversationManager: Service stopped and short-term memory flushed."
        )

    # --- IConversationManager API Implementation ---

    def start_session(
        self, session_id: str, activation_source: str = "WAKE_WORD"
    ) -> None:
        """Initialize short-term session context."""
        with self._lock:
            if not self._manager_config.enabled:
                return

            self._active_session_id = session_id
            self.store.get_or_create_session(session_id, activation_source)
            self.metrics.record_session_start()
            self.event_bus.publish(
                ConversationSessionStarted(
                    session_id=session_id, activation_source=activation_source
                )
            )
            logger.info(
                f"ConversationManager: Session context initialized for session '{session_id}'."
            )

    def end_session(self, session_id: str, reason: str = "normal_completion") -> None:
        """Flush short-term memory for session."""
        with self._lock:
            container = self.store.end_session(session_id, reason)
            turns = len(container.turns) if container else 0
            duration = (
                round(time.time() - container.created_at, 2) if container else 0.0
            )

            if self._active_session_id == session_id:
                self._active_session_id = None

            self.metrics.record_session_end(reason)
            self.event_bus.publish(
                ConversationSessionEnded(
                    session_id=session_id,
                    reason=reason,
                    turn_count=turns,
                    duration_seconds=duration,
                )
            )
            logger.info(
                f"ConversationManager: Session context flushed for '{session_id}' ({reason})."
            )

    def add_user_turn(
        self, session_id: str, text: str, turn_number: int
    ) -> ConversationTurn:
        """Record user input turn and extract entities."""
        with self._lock:
            turn = ConversationTurn(
                session_id=session_id,
                turn_number=turn_number,
                speaker=SpeakerRole.USER,
                text=text,
            )
            self.store.add_turn(session_id, turn)
            self.metrics.record_turn()
            self._extract_entities_from_text(session_id, text, turn_number)

            self.event_bus.publish(
                ConversationTurnStarted(
                    session_id=session_id,
                    turn_number=turn_number,
                    speaker="USER",
                    text=text,
                )
            )
            self._rebuild_context_snapshot(session_id)
            return turn

    def add_assistant_turn(
        self, session_id: str, text: str, turn_number: int
    ) -> ConversationTurn:
        """Record assistant response turn."""
        with self._lock:
            turn = ConversationTurn(
                session_id=session_id,
                turn_number=turn_number,
                speaker=SpeakerRole.ASSISTANT,
                text=text,
            )
            self.store.add_turn(session_id, turn)
            self._extract_entities_from_text(session_id, text, turn_number)

            container = self.store.get_session(session_id)
            user_text = ""
            if container and container.turns:
                for t in reversed(container.turns):
                    if t.speaker == SpeakerRole.USER:
                        user_text = t.text
                        break

            self.event_bus.publish(
                ConversationTurnCompleted(
                    session_id=session_id,
                    turn_number=turn_number,
                    user_text=user_text,
                    assistant_text=text,
                )
            )
            self._rebuild_context_snapshot(session_id)
            return turn

    def track_entity(self, session_id: str, entity: TrackedEntity) -> None:
        """Explicitly track an entity in active session context."""
        with self._lock:
            self.store.add_entity(session_id, entity)
            self._rebuild_context_snapshot(session_id)

    def resolve_reference(
        self, session_id: str, user_input: str
    ) -> ReferenceResolutionResult:
        """Resolve pronoun or entity reference against active session memory."""
        with self._lock:
            container = self.store.get_session(session_id)
            entities = container.entities if container else []

            res = self.resolver.resolve_reference(user_input, entities)
            self.metrics.record_reference_resolution(res.status.value)

            if res.status == ReferenceResolutionStatus.RESOLVED and res.resolved_entity:
                self.event_bus.publish(
                    ReferenceResolved(
                        session_id=session_id,
                        reference_text=res.reference_text,
                        resolved_entity_name=res.resolved_entity.name,
                        entity_category=res.resolved_entity.category.value,
                    )
                )
            elif res.status == ReferenceResolutionStatus.AMBIGUOUS:
                c_names = [c.name for c in res.candidates]
                self.event_bus.publish(
                    ReferenceAmbiguous(
                        session_id=session_id,
                        reference_text=res.reference_text,
                        candidate_names=c_names,
                    )
                )
            return res

    def get_context_snapshot(self, session_id: str) -> ContextSnapshot | None:
        """Retrieve current ContextSnapshot for session."""
        with self._lock:
            container = self.store.get_session(session_id)
            if not container:
                return None
            if not container.snapshot:
                self._rebuild_context_snapshot(session_id)
            return container.snapshot

    def record_tool_result(
        self, session_id: str, command: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Record executed tool command and tool result in short-term context."""
        with self._lock:
            self.store.add_tool_result(session_id, command, result)
            # Extract application/file entities from tool result
            app_name = command.get("arguments", {}).get("app_name") or command.get(
                "arguments", {}
            ).get("application")
            if app_name:
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name=str(app_name),
                        identifier=str(app_name).lower(),
                        source="TOOL_RESULT",
                    ),
                )
            self._rebuild_context_snapshot(session_id)

    def classify_conversational_state(
        self, session_id: str, user_input: str
    ) -> ConversationalStateCategory:
        """Classify turn relationship to previous session context."""
        clean = user_input.strip().lower()
        if not clean:
            return ConversationalStateCategory.NEW_REQUEST

        container = self.store.get_session(session_id)
        if container and container.pending_request:
            return ConversationalStateCategory.CLARIFICATION_RESPONSE

        # Corrections
        if any(
            phrase in clean
            for phrase in (
                "no, i meant",
                "no i meant",
                "actually use",
                "instead of",
                "no, use",
                "make it ",
            )
        ):
            return ConversationalStateCategory.CORRECTION

        # Retries
        if any(
            phrase in clean
            for phrase in ("try again", "do that again", "retry", "one more time")
        ):
            return ConversationalStateCategory.RETRY

        # Follow-up modifiers
        if any(
            phrase in clean
            for phrase in (
                "only today",
                "only from today",
                "make it shorter",
                "only recent",
                "just today",
            )
        ):
            return ConversationalStateCategory.FOLLOW_UP

        # Pronoun / Reference Continuation
        if self.resolver._detect_reference_trigger(clean):
            return ConversationalStateCategory.CONTINUATION

        # Topic shift or new request
        if any(
            phrase in clean
            for phrase in (
                "what is the weather",
                "hello",
                "hi",
                "goodbye",
                "tell me a joke",
            )
        ):
            return ConversationalStateCategory.NEW_TOPIC

        if container and container.turns:
            return ConversationalStateCategory.CONTINUATION

        return ConversationalStateCategory.NEW_REQUEST

    def generate_contextual_response(self, transcript: str, session_id: str) -> str:
        """Generate response incorporating reference resolution, state classification, and short-term context."""
        with self._lock:
            clean = transcript.strip()
            if not clean:
                return "Friday is online and listening."

            container = self.store.get_session(session_id)
            turn_num = len(container.turns) + 1 if container else 1
            state_cat = self.classify_conversational_state(session_id, clean)

            # 1. Handle Pending Clarification Response
            if container and container.pending_request:
                pr = container.pending_request
                container.pending_request = None
                self.metrics.record_clarification(resolved=True)
                self.event_bus.publish(
                    ClarificationResolved(
                        session_id=session_id,
                        pending_id=pr.pending_id,
                        resolved_param=clean,
                    )
                )
                target_action = pr.original_text
                return (
                    f"Opening {clean}."
                    if "open" in target_action.lower()
                    else f"Processing {target_action} for {clean}."
                )

            # 2. Handle User Correction ("No, I meant Edge")
            if state_cat == ConversationalStateCategory.CORRECTION:
                new_target = (
                    clean.split("meant")[-1].strip().strip(".")
                    if "meant" in clean
                    else clean
                )
                new_target = (
                    new_target.replace("instead", "").replace("actually", "").strip()
                )
                if "edge" in clean.lower():
                    new_target = "Edge"
                elif "chrome" in clean.lower():
                    new_target = "Chrome"

                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name=new_target.capitalize(),
                        identifier=new_target.lower(),
                        turn_number=turn_num,
                    ),
                )
                return f"Opening {new_target.capitalize()} instead."

            # 3. Handle User Retry ("Try again")
            if state_cat == ConversationalStateCategory.RETRY:
                last_cmd = ""
                if container and container.recent_commands:
                    last_cmd = container.recent_commands[-1].get("arguments", {}).get(
                        "message"
                    ) or container.recent_commands[-1].get("command", "")
                target = last_cmd if last_cmd else "previous operation"
                return f"Trying again: {target}."

            # 4. Handle Reference Resolution ("Close it", "Open the first one")
            ref_res = self.resolve_reference(session_id, clean)

            if ref_res.status == ReferenceResolutionStatus.AMBIGUOUS:
                names = " or ".join(c.name for c in ref_res.candidates[:2])
                pr = PendingRequest(
                    session_id=session_id,
                    turn_number=turn_num,
                    original_text=clean,
                    missing_fields=["target_entity"],
                    clarification_prompt=f"Which one should I target, {names}?",
                    candidate_options=[c.name for c in ref_res.candidates[:2]],
                )
                if container:
                    container.pending_request = pr
                self.metrics.record_clarification(resolved=False)
                self.event_bus.publish(
                    ClarificationRequired(
                        session_id=session_id,
                        pending_id=pr.pending_id,
                        clarification_prompt=pr.clarification_prompt,
                        missing_fields=pr.missing_fields,
                    )
                )
                return f"Which one should I target, {names}?"

            if (
                ref_res.status == ReferenceResolutionStatus.RESOLVED
                and ref_res.resolved_entity
            ):
                target = ref_res.resolved_entity.name
                lower = clean.lower()
                if "close" in lower:
                    return f"Closing {target}."
                if "open" in lower:
                    return f"Opening {target}."
                if "summarize" in lower:
                    return f"Summarizing {target}."
                return f"Processing action for {target}."

            # 5. Keyword & Multi-Entity Intent Processing
            lower = clean.lower()
            if "open chrome and edge" in lower:
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name="Chrome",
                        identifier="chrome.exe",
                        turn_number=turn_num,
                    ),
                )
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name="Edge",
                        identifier="msedge.exe",
                        turn_number=turn_num,
                    ),
                )
                return "Opening Chrome and Edge."

            if "open chrome" in lower:
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name="Chrome",
                        identifier="chrome.exe",
                        turn_number=turn_num,
                    ),
                )
                return "Opening Google Chrome."

            if "open edge" in lower:
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.APPLICATION,
                        name="Edge",
                        identifier="msedge.exe",
                        turn_number=turn_num,
                    ),
                )
                return "Opening Microsoft Edge."

            if "search for" in lower or "search" in lower:
                query = clean.split("search", 1)[-1].replace("for", "").strip()
                self.store.add_entity(
                    session_id,
                    TrackedEntity(
                        category=EntityCategory.WEBSITE,
                        name=query,
                        identifier=query,
                        turn_number=turn_num,
                    ),
                )
                return f"Searching for {query}."

            if "hello" in lower or "hi" in lower:
                return "Hello Pushkar. How can I assist you?"

            return f"Understood: {clean}"

    def _extract_entities_from_text(
        self, session_id: str, text: str, turn_number: int
    ) -> None:
        """Extract key entities (apps, websites, files) from text using keyword patterns."""
        clean = text.strip().lower()
        if "chrome" in clean:
            self.store.add_entity(
                session_id,
                TrackedEntity(
                    category=EntityCategory.APPLICATION,
                    name="Chrome",
                    identifier="chrome.exe",
                    turn_number=turn_number,
                ),
            )
        if "vscode" in clean or "vs code" in clean:
            self.store.add_entity(
                session_id,
                TrackedEntity(
                    category=EntityCategory.APPLICATION,
                    name="VS Code",
                    identifier="code.exe",
                    turn_number=turn_number,
                ),
            )
        if "notepad" in clean:
            self.store.add_entity(
                session_id,
                TrackedEntity(
                    category=EntityCategory.APPLICATION,
                    name="Notepad",
                    identifier="notepad.exe",
                    turn_number=turn_number,
                ),
            )
        file_match = re.search(r"(\w+\.(?:pdf|txt|docx|py))", clean)
        if file_match:
            fname = file_match.group(1)
            self.store.add_entity(
                session_id,
                TrackedEntity(
                    category=EntityCategory.FILE,
                    name=fname,
                    identifier=fname,
                    turn_number=turn_number,
                ),
            )

    def _rebuild_context_snapshot(self, session_id: str) -> None:
        """Re-assemble ContextSnapshot for session."""
        container = self.store.get_session(session_id)
        if not container:
            return

        snapshot = self.context_builder.build_snapshot(
            session_id=session_id,
            version=container.context_version,
            turns=container.turns,
            entities=container.entities,
            recent_commands=container.recent_commands,
            recent_results=container.recent_results,
            current_topic=container.current_topic,
            pending_request=container.pending_request,
        )
        container.snapshot = snapshot
        size_chars = len(str(snapshot))
        self.metrics.record_context_build(size_chars)

        self.event_bus.publish(
            ContextUpdated(
                session_id=session_id,
                turn_number=len(container.turns),
                context_version=container.context_version,
                entity_count=len(container.entities),
            )
        )

    # --- EventBus Event Handler Callbacks ---

    def _on_conversation_activated(self, evt: ConversationActivated) -> None:
        """Event handler when state machine activates a new session."""
        self.start_session(evt.session_id, evt.activation_source)

    def _on_conversation_ended(self, evt: ConversationEnded) -> None:
        """Event handler when state machine ends a session."""
        self.end_session(evt.session_id, evt.reason)

    def _on_transcription_completed(self, evt: TranscriptionCompleted) -> None:
        """Event handler when user speech transcript arrives."""
        if self._active_session_id:
            container = self.store.get_session(self._active_session_id)
            turn_num = len(container.turns) + 1 if container else 1
            self.add_user_turn(self._active_session_id, evt.text, turn_num)

    def _on_speaking_started(self, evt: ConversationSpeakingStarted) -> None:
        """Event handler when assistant response speaking starts."""
        if self._active_session_id and evt.text:
            container = self.store.get_session(self._active_session_id)
            turn_num = len(container.turns) + 1 if container else 1
            self.add_assistant_turn(self._active_session_id, evt.text, turn_num)

    def _on_speaking_completed(self, evt: ConversationSpeakingCompleted) -> None:
        """Event handler when assistant speaking finishes."""

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        with self._lock:
            active = self._active_session_id is not None
            sess_id = self._active_session_id
            container = self.store.get_session(sess_id) if sess_id else None

            turns = len(container.turns) if container else 0
            entities_count = len(container.entities) if container else 0
            pending = container.pending_request is not None if container else False
            ctx_size = (
                len(str(container.snapshot)) if container and container.snapshot else 0
            )

        return self.diagnostics.get_health_report(
            service_state="RUNNING" if self.is_running else "STOPPED",
            session_active=active,
            session_id=sess_id,
            turn_count=turns,
            context_turns=turns,
            active_entities_count=entities_count,
            pending_clarification=pending,
            context_size_chars=ctx_size,
            context_limit_chars=self._manager_config.max_context_characters,
            enabled=self._manager_config.enabled,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
