# 代码审查 Agent

这是软件工程 Homework 1 的第一版实现。项目通过“用户输入、模型决策、工具调用、最终输出”的循环，对工作区中的源代码进行只读审查。

## 作业信息

| 项目 | 内容 |
|---|---|
| 姓名 | 干宸骅 |
| 学号 | 2412190733 |
| 班级 | 计科2403 |
| 选题 | 代码审查 Agent |

## 已实现功能

- 命令行单次运行与多轮交互模式
- 本地 Web 界面，支持提交审查任务、查看工具调用和清空记忆
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

## 启动 Web 界面

确认 `.env` 已填写 DeepSeek API Key 后，可以直接双击项目根目录中的 `启动Web界面.bat`。启动器会自动打开浏览器，并默认把本项目作为审查工作区。运行期间请保留弹出的服务窗口；关闭窗口或在其中按 `Ctrl+C` 即可停止。

如果要审查其他项目，不需要修改启动器：在文件资源管理器中把其他项目的文件夹拖到 `启动Web界面.bat` 上。启动器会把拖入的文件夹作为工作区，Agent 只能读取该文件夹内部的文件。

也可以在项目根目录手动执行：

```powershell
py -3 -m code_review_agent --web --open-browser --workspace .
```

看到启动提示后，在浏览器访问：

```text
http://127.0.0.1:8000
```

在左侧填写审查要求，点击“开始审查”，右侧会显示报告和本次调用过的工具。点击“清空记忆”可以开始一个不带历史上下文的新会话。服务运行期间不要关闭命令行窗口，结束时在命令行按 `Ctrl+C`。

如果只想体验页面、不调用 DeepSeek，可以使用离线演示模式：

```powershell
py -3 -m code_review_agent --demo --web --workspace .
```

端口被占用时可以指定其他端口，例如 `--port 8080`。服务默认只监听 `127.0.0.1`，API Key 仅保存在服务端，不会发送到浏览器。

## 运行测试

```powershell
py -3 -m unittest discover -s tests -v
```

## 项目结构

```text
code-review-agent/
├── 启动Web界面.bat      # 双击启动，或把其他项目文件夹拖到它上面
├── code_review_agent/
│   ├── agent.py       # Agent 循环与会话记忆
│   ├── cli.py         # 命令行入口
│   ├── llm.py         # 模型接口和离线演示客户端
│   ├── prompts.py     # 系统提示词
│   ├── tools.py       # 只读代码工具与路径隔离
│   ├── web.py         # 本地 HTTP 服务和 Web API
│   └── static/
│       └── index.html # 浏览器页面
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
- Web 服务一次只执行一个 Agent 任务；前一个任务完成后才会处理下一个任务。

## 提交前检查

- 替换示例截图和演示内容，使用自己的测试项目。
- 确认 README 中的命令能在一台干净环境中运行。
- 补充 `Design.md` 中的模型服务商、测试结果和个人开发复盘。
- 确保 `.env` 与 API Key 没有进入 Git 历史。
- 准备一分钟以内的演示视频。

演示流程见 [`docs/demo-script.md`](docs/demo-script.md)，最终提交步骤见 [`docs/submission-guide.md`](docs/submission-guide.md)。

已生成的静音演示视频：[`demo/2412190733干宸骅-演示.mp4`](demo/2412190733干宸骅-演示.mp4)，分辨率为 1280×720，时长 57 秒。
