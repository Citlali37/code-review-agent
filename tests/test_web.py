import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from code_review_agent.agent import CodeReviewAgent
from code_review_agent.llm import DemoReviewClient
from code_review_agent.tools import ToolRegistry
from code_review_agent.web import create_server


class WebServerTests(unittest.TestCase):
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
        agent = CodeReviewAgent(DemoReviewClient(), ToolRegistry(self.root))
        self.server = create_server(agent, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary_directory.cleanup()

    def request_json(
        self,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_index_page_is_served(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/", timeout=3) as response:
            body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("代码审查 Agent", body)
        self.assertIn("/api/review", body)

    def test_health_endpoint(self) -> None:
        status, payload = self.request_json("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "status": "ready"})

    def test_review_endpoint_completes_agent_loop(self) -> None:
        status, payload = self.request_json(
            "/api/review",
            {"request": "审查 examples/buggy_calculator.py"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tool_steps"], ["list_files", "read_file"])
        self.assertIn("直接执行 eval", payload["report"])

    def test_empty_review_is_rejected(self) -> None:
        status, payload = self.request_json("/api/review", {"request": "   "})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertIn("不能为空", payload["error"])

    def test_reset_endpoint(self) -> None:
        status, payload = self.request_json("/api/reset", {})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("已清空", payload["message"])


if __name__ == "__main__":
    unittest.main()
