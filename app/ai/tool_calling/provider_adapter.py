"""Vendor-neutral provider adapter converting raw LLM tool formats to canonical ToolCall models.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import json
import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.ai.tool_calling.models import ToolCall
from app.logging import logger


class IToolCallAdapter(ABC):
    """Abstract boundary converting model outputs to canonical ToolCall models."""

    @abstractmethod
    def parse(self, raw_output: Any) -> ToolCall | None:
        """Parse raw vendor/LLM model response payload into canonical ToolCall."""


class DefaultToolCallAdapter(IToolCallAdapter):
    """Default adapter normalizing JSON, OpenAI, Anthropic, or Ollama tool call wire formats."""

    def parse(self, raw_output: Any) -> ToolCall | None:
        """Normalize raw output string or dict payload into canonical ToolCall model."""
        if not raw_output:
            return None

        # Case 1: Dict payload directly
        if isinstance(raw_output, dict):
            return self._parse_dict(raw_output)

        # Case 2: String payload containing JSON
        if isinstance(raw_output, str):
            clean = raw_output.strip()
            if clean.startswith("```json"):
                clean = clean.split("```json", 1)[-1].split("```", 1)[0].strip()
            elif clean.startswith("```"):
                clean = clean.split("```", 1)[-1].split("```", 1)[0].strip()

            try:
                data = json.loads(clean)
                if isinstance(data, dict):
                    return self._parse_dict(data)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    f"DefaultToolCallAdapter: Output string is not valid JSON tool call: {exc}"
                )

        return None

    def _parse_dict(self, data: dict[str, Any]) -> ToolCall | None:
        """Extract tool_name and arguments from dictionary schema variants."""
        call_id = (
            data.get("call_id") or data.get("id") or f"call_{uuid.uuid4().hex[:8]}"
        )

        # Standard Friday Format: {"tool_call": {"name": "tool_id", "arguments": {...}}}
        if "tool_call" in data and isinstance(data["tool_call"], dict):
            tc = data["tool_call"]
            name = tc.get("name") or tc.get("tool_name") or tc.get("function")
            args = tc.get("arguments") or tc.get("args") or {}
            if name:
                return ToolCall(
                    call_id=call_id,
                    tool_name=str(name),
                    arguments=args if isinstance(args, dict) else {},
                    raw_provider_payload=data,
                )

        # OpenAI / Anthropic format: {"function": {"name": "tool_id", "arguments": "{...}"}}
        if "function" in data and isinstance(data["function"], dict):
            fn = data["function"]
            name = fn.get("name")
            raw_args = fn.get("arguments", {})
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            if name:
                return ToolCall(
                    call_id=call_id,
                    tool_name=str(name),
                    arguments=args if isinstance(args, dict) else {},
                    raw_provider_payload=data,
                )

        # Direct Format: {"tool_name": "system.echo", "arguments": {...}}
        name = data.get("tool_name") or data.get("tool") or data.get("name")
        if name and "arguments" in data:
            args = data["arguments"]
            return ToolCall(
                call_id=call_id,
                tool_name=str(name),
                arguments=args if isinstance(args, dict) else {},
                raw_provider_payload=data,
            )

        return None
