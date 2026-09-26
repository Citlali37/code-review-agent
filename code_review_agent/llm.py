from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Protocol


class LLMError(RuntimeError):
    """Raised when an LLM request cannot be completed."""


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]: ...


class OpenAICompatibleClient:
    """Small dependency-free client for compatible Chat Completions APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        max_retries: int = 3,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LLM_BASE_URL 不能为空。")
        if not api_key.strip():
            raise ValueError("LLM_API_KEY 不能为空。")
        if not model.strip():
            raise ValueError("LLM_MODEL 不能为空。")
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(1, max_retries)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.1,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            request = urllib.request.Request(
                self.url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                return self._extract_message(response_data)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                last_error = LLMError(f"模型接口返回 HTTP {exc.code}：{detail}")
                if exc.code != 429 and exc.code < 500:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = LLMError(f"模型接口请求失败：{exc}")

            if attempt + 1 < self.max_retries:
                time.sleep(0.5 * (2**attempt))

        raise last_error or LLMError("模型接口请求失败。")

    @staticmethod
    def _extract_message(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("模型响应缺少 choices[0].message。") from exc
        if not isinstance(message, dict):
            raise LLMError("模型响应中的 message 格式不正确。")
        return {
            "role": "assistant",
            "content": OpenAICompatibleClient._normalize_content(message.get("content")),
            "tool_calls": message.get("tool_calls") or [],
        }

    @staticmethod
    def _normalize_content(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            pieces = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    pieces.append(item["text"])
            return "\n".join(pieces)
        return str(content)


class DemoReviewClient:
    """Deterministic offline client used to demonstrate the agent loop."""

    def __init__(self) -> None:
        self._call_number = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self._call_number += 1
        latest_user_index = max(
            (index for index, message in enumerate(messages) if message.get("role") == "user"),
            default=0,
        )
        current_turn = messages[latest_user_index + 1 :]
        tool_messages = [message for message in current_turn if message.get("role") == "tool"]

        if not tool_messages:
            return self._tool_call("list_files", {"path": ".", "pattern": "*.py"})

        if not any(message.get("name") == "read_file" for message in tool_messages):
            list_result = self._parse_tool_result(tool_messages[-1])
            files = list_result.get("data", {}).get("files", [])
            preferred = next(
                (item for item in files if item.endswith("examples/buggy_calculator.py")),
                files[0] if files else "examples/buggy_calculator.py",
            )
            return self._tool_call("read_file", {"path": preferred})

        read_message = next(
            message for message in reversed(tool_messages) if message.get("name") == "read_file"
        )
        result = self._parse_tool_result(read_message)
        if not result.get("ok"):
            return self._final_report([], "演示客户端无法读取目标文件。")
        data = result.get("data", {})
        path = data.get("path", "未知文件")
        numbered_text = data.get("text", "")
        findings = self._detect_demo_findings(path, numbered_text)
        return self._final_report(findings)

    def _tool_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": f"demo-call-{self._call_number}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    },
                }
            ],
        }

    @staticmethod
    def _parse_tool_result(message: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            return {"ok": False, "error": "工具结果不是有效 JSON。"}

    @staticmethod
    def _detect_demo_findings(path: str, numbered_text: str) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        for raw_line in numbered_text.splitlines():
            prefix, _, code = raw_line.partition(":")
            line_number = prefix.strip()
            if "eval(" in code:
                findings.append(
                    {
                        "severity": "高",
                        "location": f"{path}:{line_number}",
                        "problem": "直接执行 eval",
                        "impact": "不可信输入可能执行任意 Python 代码。",
                        "suggestion": "使用受限解析器或显式支持的运算符集合。",
                    }
                )
            if "except:" in code:
                findings.append(
                    {
                        "severity": "中",
                        "location": f"{path}:{line_number}",
                        "problem": "捕获所有异常",
                        "impact": "会隐藏编程错误，也难以定位真实失败原因。",
                        "suggestion": "只捕获预期异常，例如 ValueError。",
                    }
                )
            if "return a / b" in code:
                findings.append(
                    {
                        "severity": "中",
                        "location": f"{path}:{line_number}",
                        "problem": "没有处理除数为零",
                        "impact": "输入 0 时会触发 ZeroDivisionError。",
                        "suggestion": "在除法前验证 b，并返回清晰的错误信息。",
                    }
                )
        return findings

    @staticmethod
    def _final_report(
        findings: list[dict[str, str]],
        limitation: str = "离线演示只包含少量确定性规则，不代表真实大模型的分析能力。",
    ) -> dict[str, Any]:
        if findings:
            rows = "\n".join(
                "| {severity} | `{location}` | {problem} | {impact} | {suggestion} |".format(**item)
                for item in findings
            )
            conclusion = f"发现 {len(findings)} 个需要处理的问题，其中包含明显的安全风险。"
        else:
            rows = "| - | - | 本次演示规则未发现问题 | - | 建议接入真实模型进行完整审查 |"
            conclusion = "离线演示规则没有发现已知问题。"
        content = f"""## 审查范围

Agent 通过目录扫描和文件读取工具检查了一个 Python 示例文件。

## 总体结论

{conclusion}

## 问题清单

| 严重程度 | 位置 | 问题 | 影响 | 建议 |
|---|---|---|---|---|
{rows}

## 做得较好的地方

- 函数职责较简单，便于测试和重构。

## 未检查到的内容或限制

{limitation}
"""
        return {"role": "assistant", "content": content, "tool_calls": []}
