import tempfile
import unittest
from pathlib import Path

from code_review_agent.agent import AgentError, CodeReviewAgent
from code_review_agent.llm import DemoReviewClient
from code_review_agent.tools import ToolRegistry


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


if __name__ == "__main__":
    unittest.main()
