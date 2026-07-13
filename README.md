# Multiagent Studio

Multiagent Studio 是一个基于 CrewAI 的本地多 Agent 桌面应用与高级用户 CLI。它通过可配置 DAG 完成问题分析、方案设计、评审和摘要，并为每次运行保存版本化、可诊断的归档。

当前支持的正式 GUI 是 React + PySide6/Qt WebEngine 桌面包。GUI 不通过 wheel 分发；wheel 只提供 `multiagent-demo` CLI。

## 主要能力

- 单一、版本化的 `workflow.json` 配置，首次启动可迁移旧 `agents.json`/`tasks.json`。
- 前端按任务依赖动态绘制工作流，不假定固定任务数量或 ID。
- 独立子进程执行工作流，支持取消、请求超时、总运行超时和受限重试。
- UUID 运行目录、原子配置/事件/manifest 写入和统一运行状态机。
- `run.json`、Markdown 报告、逐任务输出、事件记录和脱敏诊断包。
- 首次 API key 设置、损坏配置恢复和生产 Bridge 协议校验。

## 本地开发环境

依赖、缓存和构建产物应留在项目目录内：

```powershell
python -m venv .venv
$env:PIP_CACHE_DIR="$PWD\.cache\pip"
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
corepack pnpm --dir frontend install --frozen-lockfile --store-dir .\.cache\pnpm-store
Copy-Item .env.template .env
```

也可安装较宽松的开发依赖声明，但可复现验证和发布必须使用 `requirements.lock`。

`.env` 至少需要：

```text
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MODEL_VARIANT=flash
CREWAI_STORAGE_DIR=.cache/crewai
```

已由进程环境注入的变量优先于 `.env`。相对存储路径会解析为应用工作目录内的绝对路径。不要提交 `.env`、`.venv`、`.cache`、`outputs` 或 `dist`。

## CLI

```powershell
.\.venv\Scripts\python.exe .\src\main.py validate
.\.venv\Scripts\python.exe .\src\main.py list-models
.\.venv\Scripts\python.exe .\src\main.py list-config
.\.venv\Scripts\python.exe .\src\main.py run --model flash "如何降低软件交付延期风险？"
```

安装 wheel 后可使用相同参数调用 `multiagent-demo`。安装版会把默认配置复制到用户应用目录；也可以设置 `MULTIAGENT_HOME` 指向明确的可写工作目录。

## 桌面应用

源码启动：

```powershell
corepack pnpm --dir frontend run build
$env:MULTIAGENT_HOME="$PWD\.cache\desktop-home"
.\.venv\Scripts\python.exe .\src\web_gui_app.py
```

构建当前平台桌面包：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_gui.py --check
.\build-gui.ps1
# 启动最新 dist 包，避免误开历史根目录 EXE
.\launch-studio.ps1 -Wait
```

构建脚本先生成前端，再运行 PyInstaller，最后生成平台归档和 SHA-256 校验文件。GitHub Actions 构建 Windows x64、Linux x64、macOS x64 和 macOS arm64。对外 GUI 只应使用经过 packaged smoke、签名/公证和校验的桌面包。

## 工作流配置

配置源为 `config/workflow.json`：

```json
{
  "schema_version": 2,
  "agents": [],
  "tasks": [
    {
      "id": "review",
      "name": "评审成稿",
      "description": "...",
      "expected_output": "...",
      "agent_id": "critical_reviewer",
      "context_task_ids": ["solution"],
      "artifact_role": "full_report",
      "enabled": true
    }
  ],
  "graph": {
    "positions": {"review": {"x": 320, "y": 80}},
    "viewport": {"x": 0, "y": 0, "zoom": 1}
  }
}
```

`artifact_role` 可为 `none`、`full_report` 或 `summary`。配置页的“工作流画布”支持拖动节点、创建/删除依赖边；边会真正写回目标任务的 `context_task_ids`，节点位置保存到 `graph.positions`。完整报告和摘要通过角色选择，不依赖固定任务 ID 或数组位置。配置校验会检查空字段、重复 ID、无效 agent、禁用依赖、缺失依赖、依赖环和重复产物角色。

## 运行归档

每次运行创建带 UUID 的目录，包含：

- `run.json`：带 `schema_version` 的权威 manifest 和状态；
- `full_report.md`、`summary_report.md`、`run_metadata.md`；
- `events.json`：包含 `run_id`、`task_id` 的公开运行事件；
- `tasks/`：逐任务输出。

状态统一为 `created → preflight → running → persisting → succeeded`，失败、取消和子进程中断分别记录为 `failed`、`cancelled`、`interrupted`。历史页优先读取 `run.json`，只对旧归档保留 Markdown 兼容解析。

## 质量与发布门槛

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src/crewai_multiagent_demo/config src/crewai_multiagent_demo/core src/crewai_multiagent_demo/domain src/crewai_multiagent_demo/llm src/crewai_multiagent_demo/utils
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing -q
.\.venv\Scripts\python.exe scripts\generate_contract_types.py --check
.\.venv\Scripts\python.exe scripts\audit_dependencies.py
corepack pnpm --dir frontend run build
corepack pnpm --dir frontend run test
```

依赖安全例外必须有明确范围和到期日，见 `docs/SECURITY_EXCEPTIONS.md`。发布流水线还生成 CycloneDX SBOM、版本信息、平台归档与 checksum。

更详细的边界和扩展规则见 `docs/ARCHITECTURE.md`。

本轮产品化整改与验证证据见 `docs/PRODUCT_AUDIT_IMPLEMENTATION_REPORT.md`。
