# CrewAI 多 Agent 通用问题解决框架

这是一个基于 CrewAI 的多 Agent 通用问题解决应用。项目已经从单文件 demo 重构为可维护的 Python 包，支持 CLI、PySide6 桌面 GUI、JSON 配置、运行输出归档、事件记录和基础测试。

默认工作流包含 4 个角色：

- `Problem Analyst`：拆解问题背景、目标、约束、关键矛盾和成功标准
- `Solution Strategist`：基于分析设计可执行方案
- `Critical Reviewer`：评审方案并生成完整正式报告
- `Executive Summarizer`：生成 500 字以内的精简报告

## 目录结构

```text
src/
  crewai_multiagent_demo/
    cli.py
    core/
      crew_builder.py
      events.py
      outputs.py
      runner.py
      workflow.py
    config/
      loader.py
      schema.py
      validation.py
    domain/
      agents.py
      tasks.py
      run_result.py
    llm/
      model_registry.py
      provider.py
    gui/
      pages.py
      services.py
      state.py
      styles.py
      widgets.py
    utils/
      environment.py
      paths.py
  main.py
  gui_app.py
config/
  agents.json
  tasks.json
tests/
```

`src/main.py` 和 `src/web_gui_app.py` 是当前入口；`src/gui_app.py` 保留为旧 Qt Widgets 界面。核心业务逻辑在 `crewai_multiagent_demo` 包内。架构分层、扩展点和验证命令见 `docs/ARCHITECTURE.md`。

## 本地环境

为了不污染全局环境，建议把虚拟环境、pip 缓存、CrewAI 缓存和输出都放在项目目录内。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
$env:PIP_CACHE_DIR="$PWD\.cache\pip"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

复制环境变量模板：

```powershell
Copy-Item .env.template .env
```

编辑 `.env`：

```text
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MODEL_VARIANT=flash
CREWAI_STORAGE_DIR=.cache/crewai
CREWAI_DISABLE_TELEMETRY=true
CREWAI_TRACING_ENABLED=false
CREWAI_TESTING=true
OTEL_SDK_DISABLED=true
```

不要提交 `.env`、`.venv`、`.cache` 或 `outputs`。

## CLI

校验配置，不调用模型：

```powershell
.\.venv\Scripts\python.exe .\src\main.py validate
```

列出模型档位：

```powershell
.\.venv\Scripts\python.exe .\src\main.py list-models
```

列出当前启用的 agents/tasks：

```powershell
.\.venv\Scripts\python.exe .\src\main.py list-config
```

运行默认主题：

```powershell
.\.venv\Scripts\python.exe .\src\main.py run
```

运行自定义主题和模型档位：

```powershell
.\.venv\Scripts\python.exe .\src\main.py run --model flash "如何降低一个小团队的软件交付延期风险？"
.\.venv\Scripts\python.exe .\src\main.py run --model pro "如何设计一个企业内部 AI Agent 平台？"
```

可选参数：

```powershell
.\.venv\Scripts\python.exe .\src\main.py run --config-dir .\config --output-dir .\outputs --model flash "你的主题"
```

旧用法仍兼容：

```powershell
.\.venv\Scripts\python.exe .\src\main.py --model flash "你的主题"
```

也可以使用 PowerShell 脚本：

```powershell
.\run.ps1 -Model flash "你的主题"
```

## 桌面 GUI

新版桌面界面使用 `PySide6 Qt WebEngine` 承载本地 React 前端，不启动本地 Web
服务，也不会把 API key 或任意本地路径暴露给界面。运行流程、配置 schema、CLI 及输出文件
均沿用原有核心逻辑。

源码开发时，前端依赖和缓存均保留在项目目录的 `frontend/node_modules/` 与 `.cache/` 中：

```powershell
corepack enable
pnpm --dir frontend install --store-dir .\.cache\pnpm-store
pnpm --dir frontend run build
.\.venv\Scripts\python.exe .\src\web_gui_app.py
```

首次构建或代码更新后，运行：

```powershell
.\build-gui.ps1
```

构建脚本会先生成前端资源，再产出当前系统的离线便携包。Windows 包位于
`dist\MultiagentStudio\MultiagentStudio.exe`；Linux 和 macOS 分别生成对应的目录包与归档。
可以先运行 `.\.venv\Scripts\python.exe .\scripts\build_gui.py --check` 检查本机打包前置条件，
该命令不会生成或覆盖发行包。
跨平台包由对应系统和架构上的 GitHub Actions 生成：Windows x64、Linux x64、macOS x64
和 macOS arm64。冻结后的应用将配置、输出与缓存写入系统用户目录；首次启动会导入旧
Windows 便携版旁置的配置，并继续读取旧 `.env` 以保证兼容。

## 配置 Agent 和 Task

默认配置文件就是示例配置：

- `config/agents.json`
- `config/tasks.json`

Agent 字段：

```json
{
  "id": "problem_analyst",
  "role": "Problem Analyst",
  "goal": "把模糊问题拆成清晰结构。",
  "backstory": "角色背景。",
  "enabled": true
}
```

Task 字段：

```json
{
  "id": "analysis",
  "name": "问题分析",
  "description": "围绕主题《{topic}》做分析。",
  "expected_output": "结构化中文问题分析。",
  "agent_id": "problem_analyst",
  "context_task_ids": [],
  "enabled": true
}
```

添加新 task 时：

1. 在 `agents.json` 中确认存在可用的 `agent_id`。
2. 在 `tasks.json` 中新增 task。
3. 用 `context_task_ids` 声明依赖的上游 task。
4. 运行 `validate` 检查配置。

配置校验会检查重复 id、空字段、不存在或未启用的 agent、缺失 task、禁用 task 被依赖、循环依赖等问题。

## 输出文件

每次运行都会在 `outputs/` 下创建时间戳目录，例如：

```text
outputs/20260515_142030/
```

包含：

- `full_report.md`
- `summary_report.md`
- `run_metadata.md`
- `events.json`
- `tasks/` 下每个 task 的单独输出

`events.json` 只记录公开运行事件和任务输出，不伪造或保存隐藏推理链。

## 模型档位

模型档位定义在 `src/crewai_multiagent_demo/llm/model_registry.py`。

默认档位：

- `flash` -> `deepseek-v4-flash`
- `pro` -> `deepseek-v4-pro`

CrewAI/LiteLLM 使用时会自动加上 `deepseek/` provider 前缀。

添加新档位时，在 `ModelRegistry` 默认模型表中增加一个 `ModelSpec` 即可。

## 测试

测试只覆盖纯逻辑，不调用 LLM：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

当前覆盖：

- config loader
- config validation
- model alias/model name 解析
- output directory creation
- event writing
- task outputs 和 run metadata writing

## 扩展点

- 新 LLM provider 或模型档位：扩展 `llm/model_registry.py`
- 新输出格式：扩展 `core/outputs.py`
- 新运行模式：扩展 `cli.py` 和 `core/runner.py`
- 新 GUI 页面：扩展 `src/gui_app.py`，保持业务逻辑调用 core 层
- 新 agent/task：修改 JSON 配置后运行 `validate`
