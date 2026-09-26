# 代码审查 Agent

这是软件工程 Homework 1 的第一版实现。项目通过“用户输入、模型决策、工具调用、最终输出”的循环，对工作区中的源代码进行只读审查。

## 已实现功能

- 命令行单次运行与多轮交互模式
- DeepSeek Chat Completions 模型接口
- `list_files`：扫描工作区文件
- `read_file`：按行读取代码
- `search_code`：跨文件搜索文本
- 最近三轮对话记忆
- 接口超时、重试和结构化错误信息
- 工作区路径隔离、文件类型和大小限制
- 不需要 API Key 的离线演示模式
- 基于 Python 标准库的自动化测试

所有代码工具均为只读工具。当前版本不会修改或执行被审查项目。

## 环境要求

- Python 3.10 或更高版本
- 使用真实模型时，需要 DeepSeek API Key

项目运行时不依赖第三方 Python 包。

## 立即运行离线演示

在项目根目录执行：

```powershell
py -3 -m code_review_agent --demo --workspace . --request "审查 examples/buggy_calculator.py" --verbose
```

离线模式会依次调用目录扫描和文件读取工具，然后用少量固定规则生成报告。它用于验证 Agent 循环，不代表真实模型的完整分析能力。

## 接入 DeepSeek

复制配置模板：

```powershell
Copy-Item .env.example .env
```

项目默认使用 `deepseek-flash`。在 `.env` 中只需要填写自己的 API Key：

```text
LLM_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的DeepSeek密钥
LLM_MODEL=deepseek-flash
LLM_THINKING=enabled
LLM_REASONING_EFFORT=high
```

不要提交 `.env`。项目已经在 `.gitignore` 中忽略该文件。

如需更深入的审查，可以把模型改为 `deepseek-v4-pro`。默认的思考模式会在工具调用之间保留 `reasoning_content`，满足 DeepSeek 多轮工具调用要求。

单次运行：

```powershell
py -3 -m code_review_agent --workspace "待审查项目目录" --request "重点检查安全问题和异常处理" --verbose
```

交互模式：

```powershell
py -3 -m code_review_agent --workspace "待审查项目目录"
```

交互模式支持：

- `:reset`：清空会话记忆
- `:quit`：退出

## 运行测试

```powershell
py -3 -m unittest discover -s tests -v
```

## 项目结构

```text
code-review-agent/
├── code_review_agent/
│   ├── agent.py       # Agent 循环与会话记忆
│   ├── cli.py         # 命令行入口
│   ├── llm.py         # 模型接口和离线演示客户端
│   ├── prompts.py     # 系统提示词
│   └── tools.py       # 只读代码工具与路径隔离
├── examples/          # 演示代码
├── tests/             # 自动化测试
├── Design.md          # 架构和设计说明
└── README.md
```

## 当前限制

- 真实模式需要可用的 DeepSeek API 账户和余额。
- 搜索工具执行普通字符串搜索，不支持正则表达式和语法树分析。
- 单个文件默认最多允许 300 KB，每次最多读取 400 行，防止上下文被大文件占满。
- 当前只提供只读工具，不直接修改代码，也不执行不可信代码。

## 提交前检查

- 替换示例截图和演示内容，使用自己的测试项目。
- 确认 README 中的命令能在一台干净环境中运行。
- 补充 `Design.md` 中的模型服务商、测试结果和个人开发复盘。
- 确保 `.env` 与 API Key 没有进入 Git 历史。
- 准备一分钟以内的演示视频。
