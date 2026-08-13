"""Conversation State Machine & Conversation Manager Subsystem for Friday AI Assistant.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
Phase 3.8 - Conversation Manager, Session Context & Short-Term Memory
"""

from app.voice.conversation.context_builder import ContextBuilder
from app.voice.conversation.conversation_manager import (
    ConversationManager,
    ManagerResponseProvider,
)
from app.voice.conversation.conversation_manager_interface import IConversationManager
from app.voice.conversation.conversation_store import InMemConversationStore
from app.voice.conversation.diagnostics import ConversationDiagnostics
from app.voice.conversation.events import (
    BargeInDetected,
    ConversationActivated,
    ConversationEnded,
    ConversationError,
    ConversationListeningStarted,
    ConversationProcessingStarted,
    ConversationSpeakingCompleted,
    ConversationSpeakingStarted,
    ConversationStateChanged,
)
from app.voice.conversation.manager_diagnostics import ConversationManagerDiagnostics
from app.voice.conversation.manager_events import (
    ClarificationRequired,
    ClarificationResolved,
    ContextEvicted,
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
    ConversationManagerConfiguration,
    ConversationTurn,
    EntityCategory,
    PendingRequest,
    ReferenceResolutionResult,
    ReferenceResolutionStatus,
    SessionStatus,
    SpeakerRole,
    TrackedEntity,
)
from app.voice.conversation.metrics import ConversationMetrics
from app.voice.conversation.models import (
    ActivationSource,
    ConversationConfiguration,
    ConversationSession,
    ConversationState,
    StateTransition,
)
from app.voice.conversation.reference_resolver import DeterministicReferenceResolver
from app.voice.conversation.response_provider_interface import (
    IConversationResponseProvider,
)
from app.voice.conversation.state_machine import ConversationStateMachine
from app.voice.conversation.state_machine_interface import IConversationStateMachine
from app.voice.conversation.test_response_provider import TestResponseProvider

__all__ = [
    "ActivationSource",
    "BargeInDetected",
    "ClarificationRequired",
    "ClarificationResolved",
    "ContextBuilder",
    "ContextEvicted",
    "ContextSnapshot",
    "ContextUpdated",
    "ConversationActivated",
    "ConversationConfiguration",
    "ConversationDiagnostics",
    "ConversationEnded",
    "ConversationError",
    "ConversationListeningStarted",
    "ConversationManager",
    "ConversationManagerConfiguration",
    "ConversationManagerDiagnostics",
    "ConversationManagerMetrics",
    "ConversationMetrics",
    "ConversationProcessingStarted",
    "ConversationSession",
    "ConversationSessionEnded",
    "ConversationSessionStarted",
    "ConversationSpeakingCompleted",
    "ConversationSpeakingStarted",
    "ConversationState",
    "ConversationStateChanged",
    "ConversationStateMachine",
    "ConversationTurn",
    "ConversationTurnCompleted",
    "ConversationTurnStarted",
    "DeterministicReferenceResolver",
    "EntityCategory",
    "IConversationManager",
    "IConversationResponseProvider",
    "IConversationStateMachine",
    "InMemConversationStore",
    "ManagerResponseProvider",
    "PendingRequest",
    "ReferenceAmbiguous",
    "ReferenceResolutionResult",
    "ReferenceResolutionStatus",
    "ReferenceResolved",
    "SessionStatus",
    "SpeakerRole",
    "StateTransition",
    "TestResponseProvider",
    "TrackedEntity",
]
