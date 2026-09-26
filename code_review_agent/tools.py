from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


TEXT_SUFFIXES = {
    "",
    ".bat",
    ".c",
    ".cfg",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".gradle",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".php",
    ".properties",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


class ToolError(ValueError):
    """Raised when a tool request is invalid or unsafe."""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """A registry of read-only tools restricted to one workspace."""

    def __init__(
        self,
        workspace: str | Path,
        max_file_bytes: int = 300_000,
        max_lines_per_read: int = 400,
    ) -> None:
        root = Path(workspace).expanduser().resolve()
        if not root.is_dir():
            raise ToolError(f"工作区不存在或不是目录：{root}")
        if max_file_bytes < 1 or max_lines_per_read < 1:
            raise ToolError("文件大小和单次读取行数限制必须大于 0。")
        self.workspace = root
        self.max_file_bytes = max_file_bytes
        self.max_lines_per_read = max_lines_per_read
        definitions = [
            ToolDefinition(
                name="list_files",
                description="列出工作区内的文件。可使用 *.py 或 **/*.ts 等 glob 模式。",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对于工作区的目录，默认为当前目录。",
                            "default": ".",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "文件名 glob 模式，默认为 *。",
                            "default": "*",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "最多返回多少个文件，范围 1 到 500。",
                            "default": 200,
                        },
                    },
                    "additionalProperties": False,
                },
                handler=self.list_files,
            ),
            ToolDefinition(
                name="read_file",
                description="读取一个文本或源代码文件，可限定起止行。",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对于工作区的文件路径。",
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "起始行，行号从 1 开始。",
                            "default": 1,
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "结束行，包含该行；省略表示读到文件末尾。",
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                handler=self.read_file,
            ),
            ToolDefinition(
                name="search_code",
                description="在工作区文本文件中搜索字符串并返回匹配位置。",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "要搜索的文本。"},
                        "path": {
                            "type": "string",
                            "description": "相对于工作区的目录或文件。",
                            "default": ".",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "要搜索的文件 glob 模式，默认为 *。",
                            "default": "*",
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "是否区分大小写。",
                            "default": False,
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "最多返回多少条匹配，范围 1 到 500。",
                            "default": 100,
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                handler=self.search_code,
            ),
        ]
        self._definitions = {item.name: item for item in definitions}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [item.schema() for item in self._definitions.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        definition = self._definitions.get(name)
        if definition is None:
            return {"ok": False, "error": f"未知工具：{name}"}
        if not isinstance(arguments, dict):
            return {"ok": False, "error": "工具参数必须是 JSON 对象。"}
        try:
            data = definition.handler(**arguments)
            return {"ok": True, "data": data}
        except (OSError, ToolError, TypeError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

    def list_files(
        self,
        path: str = ".",
        pattern: str = "*",
        max_results: int = 200,
    ) -> dict[str, Any]:
        base = self._safe_path(path)
        if not base.is_dir():
            raise ToolError(f"不是目录：{path}")
        pattern = self._validate_pattern(pattern)
        limit = self._bounded_limit(max_results)

        files: list[str] = []
        truncated = False
        for candidate in self._iter_files(base):
            relative_to_base = candidate.relative_to(base).as_posix()
            if not (
                fnmatch.fnmatch(candidate.name, pattern)
                or fnmatch.fnmatch(relative_to_base, pattern)
            ):
                continue
            if len(files) >= limit:
                truncated = True
                break
            files.append(candidate.relative_to(self.workspace).as_posix())
        return {"files": files, "count": len(files), "truncated": truncated}

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.is_file():
            raise ToolError(f"文件不存在：{path}")
        self._validate_text_file(target)
        if not isinstance(start_line, int) or start_line < 1:
            raise ToolError("start_line 必须是大于等于 1 的整数。")
        if end_line is not None and (not isinstance(end_line, int) or end_line < start_line):
            raise ToolError("end_line 必须是不小于 start_line 的整数。")

        text = self._read_text(target)
        lines = text.splitlines()
        if lines and start_line > len(lines):
            raise ToolError(f"start_line 超出文件范围，文件共有 {len(lines)} 行。")
        requested_end = (
            min(len(lines), start_line + self.max_lines_per_read - 1)
            if end_line is None
            else min(end_line, len(lines))
        )
        if requested_end - start_line + 1 > self.max_lines_per_read:
            raise ToolError(
                f"单次最多读取 {self.max_lines_per_read} 行，请缩小起止行范围。"
            )
        selected = lines[start_line - 1 : requested_end]
        numbered = "\n".join(
            f"{line_number:>5}: {line}"
            for line_number, line in enumerate(selected, start=start_line)
        )
        return {
            "path": target.relative_to(self.workspace).as_posix(),
            "start_line": start_line,
            "end_line": requested_end,
            "total_lines": len(lines),
            "truncated": requested_end < len(lines),
            "text": numbered,
        }

    def search_code(
        self,
        query: str,
        path: str = ".",
        pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip():
            raise ToolError("query 不能为空。")
        if len(query) > 200:
            raise ToolError("query 不能超过 200 个字符。")
        base = self._safe_path(path)
        if not base.exists():
            raise ToolError(f"搜索路径不存在：{path}")
        pattern = self._validate_pattern(pattern)
        limit = self._bounded_limit(max_results)

        candidates = [base] if base.is_file() else self._iter_files(base)
        needle = query if case_sensitive else query.casefold()
        matches: list[dict[str, Any]] = []
        searched_files = 0
        truncated = False
        for candidate in candidates:
            if self._should_skip(candidate) or not candidate.is_file():
                continue
            relative_to_base = candidate.name if base.is_file() else candidate.relative_to(base).as_posix()
            if not (
                fnmatch.fnmatch(candidate.name, pattern)
                or fnmatch.fnmatch(relative_to_base, pattern)
            ):
                continue
            if candidate.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = self._read_text(candidate)
            except (OSError, UnicodeError, ToolError):
                continue
            searched_files += 1
            for line_number, line in enumerate(text.splitlines(), start=1):
                haystack = line if case_sensitive else line.casefold()
                if needle not in haystack:
                    continue
                if len(matches) >= limit:
                    truncated = True
                    break
                matches.append(
                    {
                        "path": candidate.relative_to(self.workspace).as_posix(),
                        "line": line_number,
                        "text": line.strip()[:500],
                    }
                )
            if truncated:
                break
        return {
            "query": query,
            "matches": matches,
            "count": len(matches),
            "searched_files": searched_files,
            "truncated": truncated,
        }

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ToolError("路径不能为空。")
        supplied = Path(relative_path).expanduser()
        candidate = supplied.resolve() if supplied.is_absolute() else (self.workspace / supplied).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ToolError("拒绝访问工作区之外的路径。") from exc
        return candidate

    @staticmethod
    def _validate_pattern(pattern: str) -> str:
        if not isinstance(pattern, str) or not pattern.strip():
            raise ToolError("pattern 不能为空。")
        path_pattern = Path(pattern)
        if path_pattern.is_absolute() or ".." in path_pattern.parts:
            raise ToolError("pattern 不能包含绝对路径或 ..。")
        return pattern

    @staticmethod
    def _bounded_limit(value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 500:
            raise ToolError("max_results 必须是 1 到 500 之间的整数。")
        return value

    @staticmethod
    def _should_skip(path: Path) -> bool:
        return any(part in IGNORED_DIRECTORY_NAMES for part in path.parts)

    def _iter_files(self, base: Path):
        """Yield files deterministically while pruning expensive ignored trees."""
        if base.is_file():
            yield base
            return
        for root, directory_names, file_names in os.walk(base):
            directory_names[:] = sorted(
                name for name in directory_names if name not in IGNORED_DIRECTORY_NAMES
            )
            for file_name in sorted(file_names):
                candidate = Path(root) / file_name
                if not self._should_skip(candidate):
                    yield candidate

    def _validate_text_file(self, path: Path) -> None:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            raise ToolError(f"不支持读取此文件类型：{path.suffix or '[无扩展名]'}")
        size = path.stat().st_size
        if size > self.max_file_bytes:
            raise ToolError(
                f"文件过大：{size} 字节，当前上限为 {self.max_file_bytes} 字节。"
            )

    def _read_text(self, path: Path) -> str:
        self._validate_text_file(path)
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ToolError("文件无法按 UTF-8 或 GB18030 解码。")

    @staticmethod
    def to_json(result: dict[str, Any]) -> str:
        return json.dumps(result, ensure_ascii=False)
