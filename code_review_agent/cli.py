from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .agent import AgentError, CodeReviewAgent
from .llm import DemoReviewClient, LLMError, OpenAICompatibleClient
from .tools import ToolError, ToolRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-review-agent",
        description="会调用只读代码工具的命令行审查 Agent。",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="允许 Agent 读取的工作区目录，默认为当前目录。",
    )
    parser.add_argument("--request", help="单次审查要求；省略后进入交互模式。")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用离线确定性客户端演示 Agent 循环，不需要 API Key。",
    )
    parser.add_argument("--base-url", help="覆盖环境变量 LLM_BASE_URL。")
    parser.add_argument("--model", help="覆盖环境变量 LLM_MODEL。")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=8,
        help="一次任务允许的最大模型决策轮数，默认为 8。",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="在报告后显示本次调用过的工具名称。",
    )
    return parser


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def create_agent(args: argparse.Namespace) -> CodeReviewAgent:
    workspace = Path(args.workspace).expanduser().resolve()
    load_env_file(Path.cwd() / ".env")
    if workspace != Path.cwd().resolve():
        load_env_file(workspace / ".env")

    tools = ToolRegistry(workspace)
    if args.demo:
        client = DemoReviewClient()
    else:
        base_url = args.base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", "")
        model = args.model or os.getenv("LLM_MODEL", "deepseek-flash")
        missing = [
            name
            for name, value in (
                ("LLM_BASE_URL", base_url),
                ("DEEPSEEK_API_KEY", api_key),
                ("LLM_MODEL", model),
            )
            if not value
        ]
        if missing:
            joined = "、".join(missing)
            raise ValueError(
                f"缺少配置：{joined}。复制 .env.example 为 .env 后填写，"
                "或先使用 --demo 运行离线演示。"
            )
        client = OpenAICompatibleClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
            thinking=os.getenv("LLM_THINKING", "enabled") or None,
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "high") or None,
        )
    return CodeReviewAgent(client=client, tools=tools, max_steps=args.max_steps)


def print_result(agent: CodeReviewAgent, request: str, verbose: bool) -> None:
    result = agent.run(request)
    print()
    print(result.report)
    if verbose:
        used = " -> ".join(result.tool_steps) if result.tool_steps else "无"
        print(f"\n[工具调用] {used}")


def interactive_loop(agent: CodeReviewAgent, verbose: bool) -> None:
    print("代码审查 Agent 已启动。输入审查要求，或输入 :quit 退出、:reset 清空记忆。")
    while True:
        try:
            request = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not request:
            continue
        if request.lower() in {":quit", ":exit"}:
            return
        if request.lower() == ":reset":
            agent.reset_memory()
            print("会话记忆已清空。")
            continue
        try:
            print_result(agent, request, verbose)
        except (AgentError, LLMError) as exc:
            print(f"错误：{exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        agent = create_agent(args)
        if args.request:
            print_result(agent, args.request, args.verbose)
        else:
            interactive_loop(agent, args.verbose)
        return 0
    except (AgentError, LLMError, ToolError, ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
