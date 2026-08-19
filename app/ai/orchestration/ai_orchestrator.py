"""AI Orchestrator & Reasoning Workflow Engine central service.

Phase 4.2 - AI Orchestrator & Reasoning Workflow Engine
"""

import json
import threading
import time
from typing import Any

from app.ai.gateway.model_manager import LLMModelManager
from app.ai.models.models import AIRequest, ChatMessage, MessageRole
from app.ai.orchestration.events import (
    ActionPlanCreated,
    OrchestrationCompleted,
    OrchestrationFailed,
    OrchestrationStarted,
    ToolExecutionRequested,
    ToolExecutionReturned,
)
from app.ai.orchestration.metrics import OrchestratorMetrics
from app.ai.orchestration.models import (
    ActionPlan,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestratorConfiguration,
    OrchestratorState,
    ToolPlanStep,
)
from app.ai.orchestration.orchestrator_interface import IAIOrchestrator
from app.ai.personality.personality_engine import PersonalityEngine
from app.ai.response.models import ResponseGenerationRequest
from app.ai.response.response_generator import ResponseGenerator
from app.ai.tool_calling.tool_calling_engine import ToolCallingEngine
from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.registry.tool_registry import ToolRegistry
from app.voice.conversation.conversation_manager import ConversationManager


class AIOrchestrator(BaseService, IAIOrchestrator):
    """Central AI Orchestrator executing multi-step reasoning, tool selection, and response synthesis."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        llm_manager: LLMModelManager | None = None,
        tool_executor: ToolExecutor | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_calling_engine: ToolCallingEngine | None = None,
        personality_engine: PersonalityEngine | None = None,
        response_generator: ResponseGenerator | None = None,
        conversation_manager: ConversationManager | None = None,
        metrics: OrchestratorMetrics | None = None,
    ) -> None:
        super().__init__(name="AIOrchestrator", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.llm_manager = llm_manager or LLMModelManager(
            config_manager=self.config_manager, event_bus=self.event_bus
        )
        self.tool_executor = tool_executor or ToolExecutor(event_bus=self.event_bus)
        self.tool_registry = tool_registry or ToolRegistry(event_bus=self.event_bus)
        self.tool_calling_engine = tool_calling_engine or ToolCallingEngine(
            config_manager=self.config_manager,
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
        )
        self.personality_engine = personality_engine or PersonalityEngine(
            config_manager=self.config_manager,
            event_bus=self.event_bus,
        )
        self.response_generator = response_generator or ResponseGenerator(
            config_manager=self.config_manager,
            event_bus=self.event_bus,
            llm_manager=self.llm_manager,
        )
        self.conversation_manager = conversation_manager or ConversationManager(
            config_manager=self.config_manager, event_bus=self.event_bus
        )
        self.metrics = metrics or OrchestratorMetrics()

        self._lock = threading.Lock()
        self._state = OrchestratorState.IDLE
        self._config = self._load_configuration()
        self._last_error: str | None = None

    @property
    def state(self) -> OrchestratorState:
        """Current orchestrator lifecycle state."""
        with self._lock:
            return self._state

    @property
    def orchestrator_config(self) -> OrchestratorConfiguration:
        """Active configuration settings."""
        return self._config

    def _load_configuration(self) -> OrchestratorConfiguration:
        """Load configuration settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "orchestrator"):
                cfg = settings.orchestrator
                return OrchestratorConfiguration(
                    enabled=cfg.enabled,
                    max_steps=cfg.max_steps,
                    allow_tools=cfg.allow_tools,
                    system_prompt_style=cfg.system_prompt_style,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"AIOrchestrator: Failed to load configuration, using defaults: {exc}"
            )
        return OrchestratorConfiguration()

    def _do_initialize(self) -> None:
        """Initialize orchestrator dependencies."""
        logger.info("AIOrchestrator: Service initialized.")

    def _do_start(self) -> None:
        """Start service."""
        with self._lock:
            self._state = OrchestratorState.IDLE
        logger.info("AIOrchestrator: Service started and ready for requests.")

    def _do_stop(self) -> None:
        """Stop service."""
        with self._lock:
            self._state = OrchestratorState.IDLE
        logger.info("AIOrchestrator: Service stopped.")

    def process_request(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Process user request through multi-step AI reasoning and tool execution workflow."""
        t_start = time.time()
        req_id = request.request_id

        with self._lock:
            self._state = OrchestratorState.ANALYZING
            self._last_error = None

        self.event_bus.publish(
            OrchestrationStarted(
                request_id=req_id,
                user_input=request.user_input,
                session_id=request.session_id,
            )
        )

        executed_tools: list[dict[str, Any]] = []
        action_plan: ActionPlan | None = None
        turn_count = 0
        max_allowed_steps = min(request.max_steps or self._config.max_steps, 10)

        try:
            # 1. Format tool descriptions system instruction
            tools_list = (
                self.tool_registry.list_tools()
                if (request.allow_tool_execution and self._config.allow_tools)
                else []
            )
            system_instruction = self._build_system_instruction(
                tools_list, user_input=request.user_input, session_id=request.session_id
            )

            # 2. Multi-step reasoning loop
            conversation_context = list(request.messages)
            if not conversation_context:
                conversation_context.append(
                    ChatMessage(role=MessageRole.USER, content=request.user_input)
                )

            final_text = ""
            while turn_count < max_allowed_steps:
                turn_count += 1
                with self._lock:
                    self._state = OrchestratorState.PLANNING

                ai_req = AIRequest(
                    request_id=f"{req_id}-turn-{turn_count}",
                    prompt=request.user_input if turn_count == 1 else "",
                    messages=conversation_context,
                    system_instruction=system_instruction,
                    temperature=0.3,  # Lower temperature for deterministic tool decisioning
                )

                ai_resp = self.llm_manager.generate(ai_req)
                parsed_step = self._parse_llm_response(ai_resp.text)

                if parsed_step["type"] == "FINAL_RESPONSE":
                    final_text = parsed_step["content"]
                    break

                if parsed_step["type"] == "TOOL_CALL":
                    tool_name = parsed_step["tool_name"]
                    tool_args = parsed_step["arguments"]

                    if not self.tool_registry.has_tool(tool_name):
                        logger.warning(
                            f"AIOrchestrator: Tool '{tool_name}' requested but not found."
                        )
                        conversation_context.append(
                            ChatMessage(
                                role=MessageRole.ASSISTANT,
                                content=f"Attempted tool call: {tool_name}",
                            )
                        )
                        conversation_context.append(
                            ChatMessage(
                                role=MessageRole.USER,
                                content=f"Tool error: Tool '{tool_name}' is not registered in Friday.",
                            )
                        )
                        continue

                    # Create or update ActionPlan
                    if action_plan is None:
                        action_plan = ActionPlan(
                            plan_id=f"plan-{req_id}",
                            user_request=request.user_input,
                            required_tools=[tool_name],
                        )
                        self.event_bus.publish(
                            ActionPlanCreated(
                                request_id=req_id,
                                plan_id=action_plan.plan_id,
                                step_count=1,
                                required_tools=[tool_name],
                            )
                        )

                    step_info = ToolPlanStep(
                        step_number=turn_count,
                        tool_name=tool_name,
                        arguments=tool_args,
                        reasoning=parsed_step.get("reasoning", ""),
                        status="EXECUTING",
                    )
                    action_plan.steps.append(step_info)

                    # Execute Tool
                    with self._lock:
                        self._state = OrchestratorState.EXECUTING_TOOLS

                    t_tool_start = time.time()
                    self.event_bus.publish(
                        ToolExecutionRequested(
                            request_id=req_id, tool_name=tool_name, arguments=tool_args
                        )
                    )

                    tool_result = self.tool_executor.execute(
                        tool_id=tool_name, arguments=tool_args
                    )

                    tool_duration_ms = (time.time() - t_tool_start) * 1000.0
                    step_info.status = "SUCCESS" if tool_result.is_success else "FAILED"
                    step_info.result = tool_result.result

                    executed_tools.append(
                        {
                            "step": turn_count,
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "success": tool_result.is_success,
                            "result": tool_result.result,
                            "error": (
                                str(tool_result.error) if tool_result.error else None
                            ),
                        }
                    )

                    self.event_bus.publish(
                        ToolExecutionReturned(
                            request_id=req_id,
                            tool_name=tool_name,
                            status=step_info.status,
                            duration_ms=tool_duration_ms,
                        )
                    )

                    # Feed tool result back into conversation context loop
                    result_summary = (
                        json.dumps(tool_result.result)
                        if tool_result.result
                        else str(tool_result.error)
                    )
                    conversation_context.append(
                        ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=f"Called tool '{tool_name}' with args {json.dumps(tool_args)}",
                        )
                    )
                    conversation_context.append(
                        ChatMessage(
                            role=MessageRole.USER,
                            content=f"Tool '{tool_name}' execution result: {result_summary}",
                        )
                    )

            # Synthesize final response via Dynamic Response Generation Engine
            with self._lock:
                self._state = OrchestratorState.SYNTHESIZING

            if not final_text:
                pers_ctx = self.personality_engine.generate_personality_context(
                    user_input=request.user_input
                )
                resp_req = ResponseGenerationRequest(
                    request_id=f"{req_id}-synth",
                    user_input=request.user_input,
                    messages=conversation_context,
                    reasoning_summary=action_plan.user_request if action_plan else None,
                    tool_results=executed_tools,
                    personality_context=pers_ctx,
                    session_id=request.session_id,
                )
                resp_res = self.response_generator.generate_response(resp_req)
                final_text = resp_res.response_text

            duration_ms = (time.time() - t_start) * 1000.0

            with self._lock:
                self._state = OrchestratorState.COMPLETED

            self.metrics.record_request(
                duration_ms=duration_ms,
                tool_calls_count=len(executed_tools),
                success=True,
                plan_created=action_plan is not None,
            )

            self.event_bus.publish(
                OrchestrationCompleted(
                    request_id=req_id,
                    success=True,
                    tool_count=len(executed_tools),
                    duration_ms=duration_ms,
                )
            )

            return OrchestrationResult(
                request_id=req_id,
                final_response=final_text,
                success=True,
                plan=action_plan,
                executed_tools=executed_tools,
                turns_taken=turn_count,
                total_duration_ms=round(duration_ms, 2),
            )

        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.time() - t_start) * 1000.0
            err_msg = str(exc)
            logger.error(
                f"AIOrchestrator: Orchestration failed for request '{req_id}': {err_msg}"
            )

            with self._lock:
                self._state = OrchestratorState.FAILED
                self._last_error = err_msg

            self.metrics.record_request(
                duration_ms=duration_ms,
                tool_calls_count=len(executed_tools),
                success=False,
            )

            self.event_bus.publish(
                OrchestrationFailed(request_id=req_id, error_message=err_msg)
            )

            return OrchestrationResult(
                request_id=req_id,
                final_response=f"I encountered an error processing your request: {err_msg}",
                success=False,
                plan=action_plan,
                executed_tools=executed_tools,
                turns_taken=turn_count,
                total_duration_ms=round(duration_ms, 2),
                error=err_msg,
            )

    def _build_system_instruction(
        self, tools_list: list[Any], user_input: str = "", session_id: str = ""
    ) -> str:
        """Construct system prompt listing available tools, personality guidelines, conversation context, and expected response format."""
        pers_ctx = self.personality_engine.generate_personality_context(
            user_input=user_input
        )
        pers_snippet = pers_ctx.system_prompt_snippet

        prompt_parts = [
            pers_snippet,
            "",
            "Analyze the user's request carefully. If you need to perform an action or query local system info, select an available tool.",
            "Respond ONLY in one of the following two valid JSON formats:",
            "",
            "1. Tool Call format:",
            '{"tool_call": {"name": "tool_id", "arguments": {"param1": "val1"}}, "reasoning": "Why this tool is selected"}',
            "",
            "2. Final Text Answer format:",
            '{"response": "Your natural language answer to the user.", "reasoning": "Explanation"}',
            "",
        ]

        if session_id and self.conversation_manager:
            snapshot = self.conversation_manager.get_context_snapshot(session_id)
            if snapshot:
                prompt_parts.append("### SHORT-TERM CONVERSATION CONTEXT")
                if snapshot.active_entities:
                    ents = ", ".join(
                        e.get("name", "") for e in snapshot.active_entities[:5]
                    )
                    prompt_parts.append(f"- Active Entities: {ents}")
                if snapshot.pending_request:
                    pr_text = snapshot.pending_request.get("original_text", "")
                    prompt_parts.append(f"- Pending Request: {pr_text}")
                if snapshot.recent_results:
                    last_res = snapshot.recent_results[-1]
                    prompt_parts.append(f"- Recent Tool Result: {last_res}")
                prompt_parts.append("")

        if tools_list:
            prompt_parts.append("AVAILABLE TOOLS:")
            for meta in tools_list:
                name = meta.name if hasattr(meta, "name") else str(meta)
                desc = meta.description if hasattr(meta, "description") else ""
                prompt_parts.append(f"- {name}: {desc}")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, text: str) -> dict[str, Any]:
        """Parse raw LLM output text into tool call or final response structure."""
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif clean.startswith("```"):
            clean = clean.split("```", 1)[-1].split("```", 1)[0].strip()

        try:
            data = json.loads(clean)
            if "tool_call" in data:
                tc = data["tool_call"]
                return {
                    "type": "TOOL_CALL",
                    "tool_name": tc.get("name", ""),
                    "arguments": tc.get("arguments", {}),
                    "reasoning": data.get("reasoning", ""),
                }
            if "response" in data:
                return {
                    "type": "FINAL_RESPONSE",
                    "content": data["response"],
                    "reasoning": data.get("reasoning", ""),
                }
        except Exception:  # noqa: BLE001, S110
            pass

        # Fallback to direct raw text if JSON parsing is not structured
        return {
            "type": "FINAL_RESPONSE",
            "content": text.strip(),
            "reasoning": "Unstructured output fallback",
        }

    def get_health_report(self) -> dict[str, Any]:
        """Generate comprehensive diagnostic health report."""
        return {
            "status": (
                "HEALTHY"
                if self._config.enabled and self._state != OrchestratorState.FAILED
                else "DEGRADED"
            ),
            "subsystem": "AI Orchestrator & Reasoning Workflow Engine",
            "state": self._state.value,
            "enabled": self._config.enabled,
            "max_steps": self._config.max_steps,
            "allow_tools": self._config.allow_tools,
            "registered_tools_count": self.tool_registry.registered_count,
            "last_error": self._last_error,
            "metrics": self.metrics.get_metrics_snapshot(),
        }

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
