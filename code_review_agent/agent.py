from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .llm import LLMClient
from .prompts import build_system_prompt
from .tools import ToolRegistry


class AgentError(RuntimeError):
    """Raised when the agent cannot finish a review."""


@dataclass(frozen=True)
class ReviewResult:
    report: str
    tool_steps: tuple[str, ...]


class CodeReviewAgent:
    """Runs an input -> model decision -> tool -> output loop."""

    def __init__(
        self,
        client: LLMClient,
        tools: ToolRegistry,
        max_steps: int = 8,
        memory_turns: int = 3,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps 必须大于等于 1。")
        self.client = client
        self.tools = tools
        self.max_steps = max_steps
        self.memory_turns = max(0, memory_turns)
        self._memory: list[dict[str, Any]] = []

    def run(self, request: str) -> ReviewResult:
        if not request.strip():
            raise AgentError("审查要求不能为空。")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(self.tools.workspace)},
            *self._memory,
            {"role": "user", "content": request.strip()},
        ]
        tool_steps: list[str] = []

        for _ in range(self.max_steps):
            assistant_message = self.client.complete(messages, self.tools.schemas)
            content = assistant_message.get("content") or ""
            tool_calls = assistant_message.get("tool_calls") or []
            stored_assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": content,
                **({"tool_calls": tool_calls} if tool_calls else {}),
            }
            if assistant_message.get("reasoning_content") is not None:
                stored_assistant_message["reasoning_content"] = assistant_message[
                    "reasoning_content"
                ]
            messages.append(stored_assistant_message)

            if not tool_calls:
                if not content.strip():
                    raise AgentError("模型既没有输出结论，也没有调用工具。")
                self._remember(
                    request.strip(),
                    content,
                    assistant_message.get("reasoning_content"),
                )
                return ReviewResult(report=content.strip(), tool_steps=tuple(tool_steps))

            for tool_call in tool_calls:
                tool_call_id, name, arguments = self._parse_tool_call(tool_call)
                result = self.tools.call(name, arguments)
                tool_steps.append(name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": self.tools.to_json(result),
                    }
                )

        raise AgentError(
            f"Agent 在 {self.max_steps} 轮内没有完成任务。请缩小审查范围或提高 max_steps。"
        )

    def reset_memory(self) -> None:
        self._memory.clear()

    def _remember(
        self,
        request: str,
        report: str,
        reasoning_content: str | None = None,
    ) -> None:
        if self.memory_turns == 0:
            return
        assistant_memory: dict[str, Any] = {"role": "assistant", "content": report}
        if reasoning_content is not None:
            assistant_memory["reasoning_content"] = reasoning_content
        self._memory.extend(
            [
                {"role": "user", "content": request},
                assistant_memory,
            ]
        )
        self._memory = self._memory[-2 * self.memory_turns :]

    @staticmethod
    def _parse_tool_call(tool_call: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        try:
            tool_call_id = str(tool_call["id"])
            function = tool_call["function"]
            name = str(function["name"])
            raw_arguments = function.get("arguments", "{}")
            arguments = (
                json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AgentError(f"模型返回了无效的工具调用：{tool_call}") from exc
        if not isinstance(arguments, dict):
            raise AgentError("模型返回的工具参数不是 JSON 对象。")
        return tool_call_id, name, arguments
