"""Context builder for fact extraction, tool result grounding, and prompt assembly.

Phase 4.5 - Dynamic Response Generation Engine
"""

import json
from typing import Any

from app.ai.response.models import ResponseGenerationRequest, ResponseStatus
from app.tools.execution.result_normalizer import SensitiveDataSanitizer


class ResponseContextBuilder:
    """Assembles factually grounded context blocks for response LLM synthesis."""

    def determine_factual_status(
        self, tool_results: list[dict[str, Any]]
    ) -> ResponseStatus:
        """Determine overall factual execution status from tool execution results."""
        if not tool_results:
            return ResponseStatus.SUCCESS

        statuses = [res.get("status", "SUCCESS") for res in tool_results]
        successes = [s for s in statuses if s in ("SUCCESS", "COMPLETED", "TRUE")]
        failures = [
            s
            for s in statuses
            if s in ("FAILED", "ERROR", "UNKNOWN_TOOL", "INVALID_ARGUMENTS")
        ]
        denials = [s for s in statuses if s in ("AUTHORIZATION_DENIED", "DENIED")]
        timeouts = [s for s in statuses if s in ("TIMEOUT", "EXPIRED")]
        cancelled = [s for s in statuses if s in ("CANCELLED", "ABORTED")]

        if denials:
            return ResponseStatus.DENIED
        if timeouts:
            return ResponseStatus.TIMEOUT
        if cancelled:
            return ResponseStatus.CANCELLED

        if successes and failures:
            return ResponseStatus.PARTIAL_SUCCESS

        if failures and not successes:
            return ResponseStatus.FAILED

        return ResponseStatus.SUCCESS

    def build_prompt_context(self, request: ResponseGenerationRequest) -> str:
        """Build structured model prompt context block containing facts, tool results, and constraints."""
        context_parts: list[str] = []

        # 1. Personality System Prompt Snippet (if available)
        if (
            request.personality_context
            and request.personality_context.system_prompt_snippet
        ):
            context_parts.append("### SYSTEM INSTRUCTIONS")
            context_parts.append(request.personality_context.system_prompt_snippet)
            context_parts.append("")

        # 2. Factual Grounding & Anti-Hallucination Directives
        status = self.determine_factual_status(request.tool_results)
        context_parts.append("### FACTUAL GROUNDING DIRECTIVES")
        context_parts.append(f"Overall Task Execution Status: {status.value}")
        context_parts.append("- Use ONLY facts provided in TOOL RESULTS below.")
        context_parts.append(
            "- Do NOT invent or claim actions that are not present in TOOL RESULTS."
        )
        context_parts.append("- Never expose sensitive keys, tokens, or credentials.")
        context_parts.append("")

        # 3. Tool Execution Results (Sanitized & Bounded)
        if request.tool_results:
            context_parts.append("### AUTHORITATIVE TOOL RESULTS")
            for idx, res in enumerate(request.tool_results, 1):
                clean_res = SensitiveDataSanitizer.sanitize_dict(res)
                tool_name = clean_res.get("tool_name", f"tool_{idx}")
                res_status = clean_res.get("status", "SUCCESS")
                serialized = json.dumps(clean_res, default=str)
                if len(serialized) > 2000:
                    serialized = serialized[:2000] + "... [Truncated]"

                context_parts.append(
                    f'<TOOL_RESULT idx="{idx}" tool_name="{tool_name}" status="{res_status}">\n{serialized}\n</TOOL_RESULT>'
                )
            context_parts.append("")

        # 4. Optional Reasoning Summary from Orchestrator
        if request.reasoning_summary:
            context_parts.append("### REASONING SUMMARY")
            context_parts.append(request.reasoning_summary[:500])
            context_parts.append("")

        # 5. User Input Request
        context_parts.append("### USER REQUEST")
        context_parts.append(request.user_input)

        return "\n".join(context_parts)
