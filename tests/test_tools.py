import tempfile
import unittest
from pathlib import Path

from code_review_agent.tools import ToolRegistry


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "sample.py").write_text(
            "def hello():\n    return 'Hello World'\n", encoding="utf-8"
        )
        (self.root / "README.md").write_text("sample project\n", encoding="utf-8")
        self.tools = ToolRegistry(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_list_files_filters_by_pattern(self) -> None:
        result = self.tools.call("list_files", {"pattern": "*.py"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["files"], ["src/sample.py"])

    def test_read_file_adds_line_numbers(self) -> None:
        result = self.tools.call("read_file", {"path": "src/sample.py", "start_line": 2})
        self.assertTrue(result["ok"])
        self.assertIn("2:     return 'Hello World'", result["data"]["text"])

    def test_read_file_limits_each_chunk(self) -> None:
        long_file = self.root / "long.py"
        long_file.write_text("\n".join(f"line_{number}" for number in range(10)), encoding="utf-8")
        tools = ToolRegistry(self.root, max_lines_per_read=3)
        result = tools.call("read_file", {"path": "long.py"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["end_line"], 3)
        self.assertTrue(result["data"]["truncated"])

        oversized_range = tools.call(
            "read_file", {"path": "long.py", "start_line": 1, "end_line": 4}
        )
        self.assertFalse(oversized_range["ok"])
        self.assertIn("单次最多读取", oversized_range["error"])

    def test_search_code_is_case_insensitive_by_default(self) -> None:
        result = self.tools.call("search_code", {"query": "hello world"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["matches"][0]["line"], 2)

    def test_path_outside_workspace_is_rejected(self) -> None:
        result = self.tools.call("read_file", {"path": "../secret.txt"})
        self.assertFalse(result["ok"])
        self.assertIn("工作区之外", result["error"])

    def test_unknown_tool_returns_structured_error(self) -> None:
        result = self.tools.call("delete_file", {})
        self.assertFalse(result["ok"])
        self.assertIn("未知工具", result["error"])


if __name__ == "__main__":
    unittest.main()
