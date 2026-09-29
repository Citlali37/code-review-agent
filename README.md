# 代码审查 Agent

一个基于 DeepSeek 的本地代码审查工具。模型会根据审查要求自主读取、搜索工作区中的代码，并生成 Markdown 格式的审查报告。

项目提供 Web 和命令行两种使用方式。所有代码工具均为只读，不会修改或执行被审查项目。

## 功能

- 使用 DeepSeek 完成代码分析
- 支持目录扫描、文件读取和代码搜索
- 支持 Web 页面、单次命令和多轮交互
- 保留最近三轮对话上下文
- 提供超时、重试和结构化错误信息
- 限制可访问目录、文件类型、文件大小和读取行数
- 提供无需 API Key 的离线演示模式

## 环境

- Python 3.10 或更高版本
- DeepSeek API Key，离线演示模式不需要

项目运行时不依赖第三方 Python 包。

## 快速开始

复制配置模板：

```powershell
Copy-Item .env.example .env
```

打开 `.env`，填写自己的 DeepSeek API Key：

```text
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

`.env` 只保存在本地，并已被 Git 忽略。不要把自己的 API Key 分享给其他人。

### Web 界面

直接双击项目根目录中的 `启动Web界面.bat`，浏览器会自动打开：

```text
http://127.0.0.1:8000
```

默认工作区是本项目。要审查其他项目，可以把目标项目文件夹拖到 `启动Web界面.bat` 上。

也可以手动启动：

```powershell
py -3 -m code_review_agent --web --open-browser --workspace .
```

### 命令行

执行一次审查：

```powershell
py -3 -m code_review_agent --workspace "待审查项目目录" --request "重点检查安全问题和异常处理" --verbose
```

进入多轮交互模式：

```powershell
py -3 -m code_review_agent --workspace "待审查项目目录"
```

交互模式支持 `:reset` 清空记忆、`:quit` 退出。

### 离线演示

没有 API Key 时可以运行：

```powershell
py -3 -m code_review_agent --demo --web --open-browser --workspace .
```

离线模式会真实调用本地工具，但只使用固定规则生成报告，不代表 DeepSeek 的完整分析能力。

## 工作流程

```text
用户请求 → DeepSeek 决定调用工具 → Agent 读取或搜索代码
        → 工具结果返回 DeepSeek → 生成审查报告
```

核心代码位于 `code_review_agent/`：

- `agent.py`：Agent 循环和会话记忆
- `llm.py`：DeepSeek 接口和离线客户端
- `tools.py`：只读代码工具和路径隔离
- `web.py`：本地 Web 服务
- `static/index.html`：浏览器页面

## 测试

```powershell
py -3 -m unittest discover -s tests -v
```

## 限制

- 真实模式需要可用的 DeepSeek 账户和余额。
- 搜索工具只支持普通字符串搜索，不支持正则表达式和语法树分析。
- 单个文件默认不超过 300 KB，每次最多读取 400 行。
- Web 服务一次只执行一个 Agent 任务。
