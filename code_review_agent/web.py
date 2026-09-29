from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .agent import AgentError, CodeReviewAgent
from .llm import LLMError


MAX_REQUEST_BYTES = 16_384
MAX_REQUEST_CHARACTERS = 4_000
INDEX_PATH = Path(__file__).with_name("static") / "index.html"


class ReviewWebApp:
    """Small application layer shared by the HTTP handler and tests."""

    def __init__(self, agent: CodeReviewAgent) -> None:
        self.agent = agent
        self._agent_lock = threading.Lock()
        self.index_html = INDEX_PATH.read_bytes()

    def review(self, request: object) -> dict[str, Any]:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("审查要求不能为空。")
        normalized = request.strip()
        if len(normalized) > MAX_REQUEST_CHARACTERS:
            raise ValueError(f"审查要求不能超过 {MAX_REQUEST_CHARACTERS} 个字符。")
        with self._agent_lock:
            result = self.agent.run(normalized)
        return {
            "ok": True,
            "report": result.report,
            "tool_steps": list(result.tool_steps),
        }

    def reset(self) -> dict[str, Any]:
        with self._agent_lock:
            self.agent.reset_memory()
        return {"ok": True, "message": "会话记忆已清空。"}


class ReviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_handler(app: ReviewWebApp):
    class ReviewRequestHandler(BaseHTTPRequestHandler):
        server_version = "CodeReviewAgent/0.2"

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send_bytes(
                    HTTPStatus.OK,
                    app.index_html,
                    "text/html; charset=utf-8",
                )
                return
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, {"ok": True, "status": "ready"})
                return
            if path == "/favicon.ico":
                self._send_bytes(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "页面不存在。"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/api/review":
                    payload = self._read_json()
                    result = app.review(payload.get("request"))
                    self._send_json(HTTPStatus.OK, result)
                    return
                if path == "/api/reset":
                    self._read_json(allow_empty=True)
                    self._send_json(HTTPStatus.OK, app.reset())
                    return
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"ok": False, "error": "接口不存在。"},
                )
            except ValueError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"ok": False, "error": str(exc)},
                )
            except (AgentError, LLMError) as exc:
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {"ok": False, "error": str(exc)},
                )

        def _read_json(self, *, allow_empty: bool = False) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                if allow_empty:
                    return {}
                raise ValueError("请求缺少 Content-Length。")
            try:
                content_length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Content-Length 格式错误。") from exc
            if content_length < 0 or content_length > MAX_REQUEST_BYTES:
                raise ValueError(f"请求体不能超过 {MAX_REQUEST_BYTES} 字节。")
            if content_length == 0:
                if allow_empty:
                    return {}
                raise ValueError("请求体不能为空。")
            content_type = self.headers.get("Content-Type", "")
            if "application/json" not in content_type.lower():
                raise ValueError("请求必须使用 application/json。")
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("请求体不是有效的 UTF-8 JSON。") from exc
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是 JSON 对象。")
            return payload

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(status, body, "application/json; charset=utf-8")

        def _send_bytes(
            self,
            status: HTTPStatus,
            body: bytes,
            content_type: str,
        ) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def log_message(self, format_string: str, *args: Any) -> None:
            sys.stderr.write(
                f"[web] {self.address_string()} - {format_string % args}\n"
            )

    return ReviewRequestHandler


def create_server(
    agent: CodeReviewAgent,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ReviewHTTPServer:
    if not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port 必须是 0 到 65535 之间的整数。")
    app = ReviewWebApp(agent)
    return ReviewHTTPServer((host, port), create_handler(app))


def run_web_server(
    agent: CodeReviewAgent,
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    open_browser: bool = False,
) -> None:
    server = create_server(agent, host=host, port=port)
    actual_host, actual_port = server.server_address[:2]
    if host not in {"127.0.0.1", "localhost", "::1"}:
        print(
            "警告：Web 服务并非只监听本机，请确认所在网络可信。",
            file=sys.stderr,
        )
    url = f"http://{actual_host}:{actual_port}"
    print(f"代码审查 Agent Web 已启动：{url}")
    print("按 Ctrl+C 停止服务。")
    if open_browser and not webbrowser.open(url):
        print(f"无法自动打开浏览器，请手动访问：{url}", file=sys.stderr)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nWeb 服务已停止。")
    finally:
        server.server_close()
