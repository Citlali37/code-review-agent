import tempfile
import unittest
from pathlib import Path
from typing import Any

from code_review_agent.agent import AgentError, CodeReviewAgent
from code_review_agent.llm import DemoReviewClient
from code_review_agent.tools import ToolRegistry


class ThinkingToolClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "content": "",
                "reasoning_content": "state-that-must-be-returned",
                "tool_calls": [
                    {
                        "id": "thinking-call-1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path":"examples/buggy_calculator.py"}',
                        },
                    }
                ],
            }
        if self.calls == 2:
            assistant_messages = [
                message for message in messages if message.get("role") == "assistant"
            ]
            if (
                assistant_messages[-1].get("reasoning_content")
                != "state-that-must-be-returned"
            ):
                raise AssertionError("reasoning_content was not preserved")
            return {
                "role": "assistant",
                "content": "审查完成",
                "reasoning_content": "final-state-for-memory",
                "tool_calls": [],
            }
        previous_finals = [
            message
            for message in messages
            if message.get("role") == "assistant" and message.get("content") == "审查完成"
        ]
        if (
            not previous_finals
            or previous_finals[-1].get("reasoning_content") != "final-state-for-memory"
        ):
            raise AssertionError("final reasoning_content was not preserved in memory")
        return {"role": "assistant", "content": "继续完成", "tool_calls": []}


class CodeReviewAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        example = self.root / "examples"
        example.mkdir()
        (example / "buggy_calculator.py").write_text(
            "def divide(a, b):\n"
            "    return a / b\n\n"
            "def calculate(expression):\n"
            "    return eval(expression)\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_demo_client_completes_tool_loop(self) -> None:
        agent = CodeReviewAgent(
            client=DemoReviewClient(),
            tools=ToolRegistry(self.root),
            max_steps=5,
        )
        result = agent.run("审查示例代码")
        self.assertEqual(result.tool_steps, ("list_files", "read_file"))
        self.assertIn("直接执行 eval", result.report)
        self.assertIn("没有处理除数为零", result.report)

    def test_empty_request_is_rejected(self) -> None:
        agent = CodeReviewAgent(DemoReviewClient(), ToolRegistry(self.root))
        with self.assertRaises(AgentError):
            agent.run("   ")

    def test_thinking_content_is_preserved_across_tool_turns(self) -> None:
        agent = CodeReviewAgent(ThinkingToolClient(), ToolRegistry(self.root))
        result = agent.run("审查示例代码")
        self.assertEqual(result.report, "审查完成")
        self.assertEqual(result.tool_steps, ("read_file",))
        follow_up = agent.run("继续说明")
        self.assertEqual(follow_up.report, "继续完成")


if __name__ == "__main__":
    unittest.main()
