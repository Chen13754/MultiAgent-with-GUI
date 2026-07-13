# Multiagent Studio 产品化整改报告

## 结论

本轮整改已解决截图中的运行阻断，并把工作流图从只读进度展示升级为可编辑、有状态、可持久化的 DAG。当前源码和本地 Windows 开发发行包达到可复现 Beta 验收标准；正式对外发布仍需完成代码签名、公证和受控真实模型 canary。

## 已修复问题

### 运行与打包

- PyInstaller 明确收集 `crewai` 数据文件，包含 `translations/en.json`，修复 `Prompt file 'None' not found`。
- 移除错误的 `--exclude-module chromadb`，修复 CrewAI 导入链在 packaged E2E 中的 `No module named 'chromadb'`。
- 前端构建在 prerequisite 检查之后执行，干净 checkout 可直接构建。
- 发行物写入版本、目标平台和 checksum；版本更新为 `0.2.0`。
- 根目录旧 EXE 已移入 `.cache/legacy-bundle/20260604`，新增 `launch-studio.ps1` 只启动最新 `dist` 包。

### 工作流结构与运行一致性

- `workflow.json` 支持 schema 2，`graph.positions` 只保存布局，任务拓扑仍由 `context_task_ids` 唯一决定。
- ReactFlow 支持连接、删边、拖动节点；连接会经过重复边、自环和环依赖检查，并真实保存到 Python 配置层。
- 画布保存支持 revision 冲突检测，避免多窗口覆盖。
- `RunRequest` 冻结已校验的 `AppConfig` 和 `config_revision`，子进程不再重新读取新配置。
- CrewAI 事件总线映射 `task_started`、`task_completed`、`task_failed`，运行图按任务状态显示 waiting/running/succeeded/failed/cancelled。

### 中文界面与可读性

- 中文字体优先，修正标题负字距和过重控件字重。
- 放大节点和连接点，区分任务状态边线，减少持续 sheen/pulse 动画。
- 低宽度下改为单列布局，凭据区和图表不再挤压。
- 导航、tab、错误提示和图表增加可访问名称及屏幕阅读器任务列表。

## 验证证据

| 检查 | 结果 |
|---|---|
| Python 测试 | 54 passed |
| 前端 Vitest | 2 passed |
| TypeScript/Vite build | passed |
| Ruff / mypy | passed |
| compileall / pip check | passed |
| contract generation check | passed |
| packaged smoke | exit 0 |
| packaged loopback provider E2E | succeeded |
| CrewAI translation resource | 已存在于发行包 |
| Qt WebEngine 页面监控 | 4 个工作流节点真实渲染 |

视觉证据见 [运行态截图](../.cache/visual-audit-after-run.png)。

## 发布状态

当前构建是未签名的 Windows x64 开发包。以下门槛已在 CI 中配置，但需要外部凭据才能完成：

1. Windows Authenticode 签名；
2. macOS 签名与 notarization；
3. 受控真实 DeepSeek canary。

在这些门槛完成前，发布决策仍为 No-Go；本地开发、结构编辑和假服务端到端运行可继续使用。
