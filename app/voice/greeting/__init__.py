"""Natural Greetings Foundation Subsystem for Friday AI Assistant.

Phase 3.9 - Natural Greetings Foundation & Context-Aware Activation Responses
"""

from app.voice.greeting.diagnostics import GreetingDiagnostics
from app.voice.greeting.events import (
    GreetingGenerated,
    GreetingGenerationFailed,
    GreetingGenerationStarted,
    GreetingSkipped,
    GreetingSpoken,
)
from app.voice.greeting.greeting_context_builder import GreetingContextBuilder
from app.voice.greeting.greeting_provider_interface import IGreetingProvider
from app.voice.greeting.greeting_selector import GreetingSelector
from app.voice.greeting.greeting_service import GreetingService
from app.voice.greeting.metrics import GreetingMetrics
from app.voice.greeting.models import (
    GreetingCategory,
    GreetingConfiguration,
    GreetingContext,
    GreetingResponse,
    GreetingStyle,
    TimeOfDay,
)
from app.voice.greeting.template_provider import TemplateGreetingProvider

__all__ = [
    "GreetingCategory",
    "GreetingConfiguration",
    "GreetingContext",
    "GreetingContextBuilder",
    "GreetingDiagnostics",
    "GreetingGenerated",
    "GreetingGenerationFailed",
    "GreetingGenerationStarted",
    "GreetingMetrics",
    "GreetingResponse",
    "GreetingSelector",
    "GreetingService",
    "GreetingSkipped",
    "GreetingSpoken",
    "GreetingStyle",
    "IGreetingProvider",
    "TemplateGreetingProvider",
    "TimeOfDay",
]
