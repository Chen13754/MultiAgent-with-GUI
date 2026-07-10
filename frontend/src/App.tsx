import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import ReactMarkdown from "react-markdown";
import { Background, BackgroundVariant, Controls, ReactFlow, type Edge, type Node } from "@xyflow/react";
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  FileText,
  FolderOpen,
  History,
  LayoutDashboard,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  Save,
  Settings2,
  Sparkles,
  Trash2
} from "lucide-react";

import { getBridge, type StudioBridge } from "./bridge";
import type { AgentConfig, AppSnapshot, ConfigSnapshot, HistoryDetail, HistoryItem, Notice, RunState, TaskConfig } from "./types";

type Page = "run" | "config" | "history";
type ConfigTab = "agents" | "tasks" | "json" | "validation";

const statusLabels: Record<RunState["status"], string> = {
  idle: "待运行",
  running: "运行中",
  succeeded: "已完成",
  failed: "运行失败"
};

function formatSeconds(value: number | null | undefined): string {
  return typeof value === "number" ? `${value.toFixed(1)} 秒` : "—";
}

function cloneAgents(agents: AgentConfig[]): AgentConfig[] {
  return agents.map((agent) => ({ ...agent }));
}

function cloneTasks(tasks: TaskConfig[]): TaskConfig[] {
  return tasks.map((task) => ({ ...task, context_task_ids: [...task.context_task_ids] }));
}

function normaliseTasks(value: unknown): TaskConfig[] {
  if (!Array.isArray(value)) throw new Error("Tasks 顶层必须是数组。");
  return value.map((item) => {
    const task = item as Record<string, unknown>;
    const context = task.context_task_ids;
    return {
      id: String(task.id ?? ""),
      name: String(task.name ?? task.id ?? ""),
      description: String(task.description ?? ""),
      expected_output: String(task.expected_output ?? ""),
      agent_id: String(task.agent_id ?? ""),
      context_task_ids: Array.isArray(context)
        ? context.map(String).filter(Boolean)
        : String(context ?? "").split(",").map((part) => part.trim()).filter(Boolean),
      enabled: task.enabled !== false
    };
  });
}

function statusClass(status: RunState["status"] | HistoryItem["status"]): string {
  return `status status-${status}`;
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: string }) {
  return <div className={`metric metric-${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}

function SectionHeading({ kicker, title, detail, action }: { kicker?: string; title: string; detail?: string; action?: React.ReactNode }) {
  return <div className="section-heading">
    <div>
      {kicker && <span className="kicker">{kicker}</span>}
      <h2>{title}</h2>
      {detail && <p>{detail}</p>}
    </div>
    {action}
  </div>;
}

function WorkflowGraph({ state }: { state: RunState }) {
  const stages = ["分析", "策略", "评审", "总结"];
  const completed = state.events.filter((event) => event.type === "task_completed").length;
  const nodes = useMemo<Node[]>(() => stages.map((label, index) => {
    const done = state.status === "succeeded" || index < completed;
    const active = state.status === "running" && index === Math.min(completed, stages.length - 1);
    return {
      id: label,
      position: [{ x: 30, y: 150 }, { x: 190, y: 50 }, { x: 370, y: 95 }, { x: 535, y: 180 }][index],
      data: { label: `${done ? "✓ " : active ? "• " : ""}${label}` },
      className: `flow-node ${done ? "is-done" : ""} ${active ? "is-active" : ""}`
    };
  }), [completed, state.status]);
  const edges = useMemo<Edge[]>(() => stages.slice(0, -1).map((label, index) => ({
    id: `${label}-${stages[index + 1]}`,
    source: label,
    target: stages[index + 1],
    animated: state.status === "running",
    className: state.status === "failed" ? "is-failed" : ""
  })), [state.status]);

  return <div className="flow-shell" aria-label="多 Agent 编排流程">
    <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.22 }} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} proOptions={{ hideAttribution: true }}>
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="rgba(75, 86, 110, .22)" />
      <Controls showInteractive={false} />
    </ReactFlow>
  </div>;
}

function RunPage({ snapshot, state, bridge, onNotice }: { snapshot: AppSnapshot; state: RunState; bridge: StudioBridge; onNotice: (notice: Notice) => void }) {
  const [topic, setTopic] = useState("分析并解决一个需要多方权衡的复杂问题");
  const [model, setModel] = useState(snapshot.defaultModel);
  const [resultOpen, setResultOpen] = useState(Boolean(state.result));
  const [resultTab, setResultTab] = useState<"summary" | "full" | "tasks">("summary");
  const resultRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!state.result) return;
    setResultOpen(true);
    window.requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
  }, [state.result]);
  const running = state.status === "running";

  const run = async () => {
    const response = await bridge.startRun(topic, model);
    if (!response.ok) onNotice({ kind: "error", message: response.message ?? "无法启动工作流。" });
  };
  const reset = async () => {
    const response = await bridge.resetRun();
    if (!response.ok) onNotice({ kind: "warning", message: response.message ?? "当前不能重置。" });
  };

  return <motion.main key="run" className="page" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
    <SectionHeading kicker="ORCHESTRATION" title="让多 Agent 协作变得可见" detail="输入主题，实时观察编排、事件和最终报告。" action={<button className="button ghost" onClick={() => void bridge.openLocation("outputs")}><FolderOpen size={17} /> 打开输出目录</button>} />
    <section className="metrics-row" aria-label="当前运行概况">
      <Metric label="状态" value={statusLabels[state.status]} tone={state.status} />
      <Metric label="模型" value={state.modelAlias || model} />
      <Metric label="任务" value={`${state.taskCount || snapshot.config.enabledTaskCount}`} />
      <Metric label="进度" value={`${state.progress}%`} tone={state.status === "running" ? "running" : "neutral"} />
    </section>
    <section className="run-layout">
      <div className="panel control-panel">
        <div className="panel-title"><Sparkles size={19} /><span>运行控制</span></div>
        <label>模型档位<select value={model} disabled={running} onChange={(event) => setModel(event.target.value)}>{snapshot.models.map((alias) => <option value={alias} key={alias}>{alias}{snapshot.apiKeyConfigured[alias] ? "" : "（未配置 key）"}</option>)}</select></label>
        <label>任务主题<textarea value={topic} disabled={running} onChange={(event) => setTopic(event.target.value)} rows={7} /></label>
        <div className="api-note"><Cpu size={16} /> API key 仅由本地 Python 读取，不会发送到界面。</div>
        <button className={`button primary ${running ? "is-running" : ""}`} disabled={running} onClick={() => void run()}>{running ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}{running ? "工作流运行中" : "运行工作流"}</button>
        <button className="button secondary" disabled={running && state.progress > 0} onClick={() => void reset()}><RefreshCw size={17} /> 重置本次工作区</button>
      </div>
      <div className="panel orchestration-panel">
        <div className="panel-head"><div><span className="eyebrow">LIVE FLOW</span><h3>实时编排</h3></div><span className={statusClass(state.status)}>{statusLabels[state.status]}</span></div>
        <WorkflowGraph state={state} />
        <div className="progress-wrap"><div className="progress-label"><span>{state.activeAgent}</span><strong>{state.progress}%</strong></div><div className="progress-track"><motion.div className="progress-value" animate={{ width: `${state.progress}%` }} /></div></div>
      </div>
      <div className="panel events-panel">
        <div className="panel-head"><div><span className="eyebrow">PUBLIC EVENTS</span><h3>事件流</h3></div><span>{state.events.length} 条</span></div>
        <div className="event-list">
          {state.events.length === 0 && <div className="empty-state">运行后，这里会显示公开事件、任务完成和输出节点。</div>}
          <AnimatePresence initial={false}>{state.events.slice(-8).map((event, index) => <motion.div className="event-item" key={`${String(event.time ?? "")}-${index}`} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}><span className="event-dot" /><div><strong>{String(event.agent ?? event.type ?? "事件")}</strong><small>{String(event.type ?? "")}</small></div></motion.div>)}</AnimatePresence>
        </div>
      </div>
    </section>
    <AnimatePresence>
      {state.result && resultOpen && <motion.section ref={resultRef} className="result-drawer" initial={{ opacity: 0, y: 32 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 24 }} transition={{ type: "spring", stiffness: 260, damping: 28 }}>
        <div className="drawer-head"><div><span className="eyebrow">RESULT READY</span><h3>报告已生成</h3><p>{state.result.modelAlias} · {formatSeconds(state.result.elapsedSeconds)}</p></div><button className="button ghost" onClick={() => setResultOpen(false)}>收起</button></div>
        <div className="tabs compact result-tabs" role="tablist">{(["summary", "full", "tasks"] as const).map((item) => <button key={item} className={resultTab === item ? "active" : ""} onClick={() => setResultTab(item)} role="tab">{{ summary: "精简报告", full: "完整报告", tasks: "任务输出" }[item]}</button>)}</div>
        <article className="report-content result-content">{resultTab === "summary" && <ReactMarkdown>{state.result.summary}</ReactMarkdown>}{resultTab === "full" && <ReactMarkdown>{state.result.fullReport}</ReactMarkdown>}{resultTab === "tasks" && state.result.taskOutputs.map((task, index) => <details key={`${task.task_id ?? index}`} open={index === 0}><summary>{task.task_name ?? task.agent ?? `任务 ${index + 1}`}</summary><ReactMarkdown>{task.output}</ReactMarkdown></details>)}</article>
      </motion.section>}
    </AnimatePresence>
  </motion.main>;
}

function AgentTable({ rows, onChange }: { rows: AgentConfig[]; onChange: (rows: AgentConfig[]) => void }) {
  const update = (index: number, key: keyof AgentConfig, value: string | boolean) => onChange(rows.map((row, current) => current === index ? { ...row, [key]: value } : row));
  return <div className="table-scroll"><table><thead><tr><th>ID</th><th>角色</th><th>目标</th><th>背景</th><th>启用</th><th /></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.id}-${index}`}><td><input value={row.id} onChange={(event) => update(index, "id", event.target.value)} /></td><td><input value={row.role} onChange={(event) => update(index, "role", event.target.value)} /></td><td><input value={row.goal} onChange={(event) => update(index, "goal", event.target.value)} /></td><td><input value={row.backstory} onChange={(event) => update(index, "backstory", event.target.value)} /></td><td><input className="toggle" aria-label={`${row.id} enabled`} type="checkbox" checked={row.enabled} onChange={(event) => update(index, "enabled", event.target.checked)} /></td><td><button className="icon-button" aria-label="删除 Agent" onClick={() => onChange(rows.filter((_, current) => current !== index))}><Trash2 size={16} /></button></td></tr>)}</tbody></table></div>;
}

function TaskTable({ rows, agents, onChange }: { rows: TaskConfig[]; agents: AgentConfig[]; onChange: (rows: TaskConfig[]) => void }) {
  const update = (index: number, key: keyof TaskConfig, value: string | boolean | string[]) => onChange(rows.map((row, current) => current === index ? { ...row, [key]: value } : row));
  return <div className="table-scroll"><table><thead><tr><th>ID</th><th>名称</th><th>说明</th><th>预期输出</th><th>Agent</th><th>上下文任务</th><th>启用</th><th /></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.id}-${index}`}><td><input value={row.id} onChange={(event) => update(index, "id", event.target.value)} /></td><td><input value={row.name} onChange={(event) => update(index, "name", event.target.value)} /></td><td><input value={row.description} onChange={(event) => update(index, "description", event.target.value)} /></td><td><input value={row.expected_output} onChange={(event) => update(index, "expected_output", event.target.value)} /></td><td><select value={row.agent_id} onChange={(event) => update(index, "agent_id", event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.id}</option>)}</select></td><td><input value={row.context_task_ids.join(", ")} onChange={(event) => update(index, "context_task_ids", event.target.value.split(",").map((part) => part.trim()).filter(Boolean))} /></td><td><input className="toggle" aria-label={`${row.id} enabled`} type="checkbox" checked={row.enabled} onChange={(event) => update(index, "enabled", event.target.checked)} /></td><td><button className="icon-button" aria-label="删除 Task" onClick={() => onChange(rows.filter((_, current) => current !== index))}><Trash2 size={16} /></button></td></tr>)}</tbody></table></div>;
}

function ConfigPage({ snapshot, state, bridge, onConfig, onNotice }: { snapshot: AppSnapshot; state: RunState; bridge: StudioBridge; onConfig: (config: ConfigSnapshot) => void; onNotice: (notice: Notice) => void }) {
  const [tab, setTab] = useState<ConfigTab>("agents");
  const [agents, setAgents] = useState(() => cloneAgents(snapshot.config.agents));
  const [tasks, setTasks] = useState(() => cloneTasks(snapshot.config.tasks));
  const [agentsJson, setAgentsJson] = useState(snapshot.config.agentsJson);
  const [tasksJson, setTasksJson] = useState(snapshot.config.tasksJson);
  const [validation, setValidation] = useState(snapshot.config.validationText);
  const locked = state.status === "running";

  useEffect(() => { setAgents(cloneAgents(snapshot.config.agents)); setTasks(cloneTasks(snapshot.config.tasks)); setAgentsJson(snapshot.config.agentsJson); setTasksJson(snapshot.config.tasksJson); setValidation(snapshot.config.validationText); }, [snapshot.config]);
  const save = async (kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[]) => {
    const response = await bridge.saveConfig(kind, payload);
    if (!response.ok || !response.data) { onNotice({ kind: "error", message: response.message ?? "保存失败。" }); return; }
    onConfig(response.data); onNotice({ kind: "success", message: `${kind === "agents" ? "Agents" : "Tasks"} 已保存。` });
  };
  const saveJson = async () => {
    try {
      if (tab === "json") {
        const response = await bridge.saveConfigBundle(JSON.parse(agentsJson) as AgentConfig[], normaliseTasks(JSON.parse(tasksJson)));
        if (!response.ok || !response.data) { onNotice({ kind: "error", message: response.message ?? "保存失败。" }); return; }
        onConfig(response.data);
        onNotice({ kind: "success", message: "Agents 和 Tasks 已一起保存。" });
      }
    } catch (error) { onNotice({ kind: "error", message: error instanceof Error ? error.message : "JSON 格式错误。" }); }
  };
  const validate = async () => { const response = await bridge.validateConfig(); if (response.ok && response.data) { setValidation(response.data.text); onNotice({ kind: "success", message: "配置检查通过。" }); } else onNotice({ kind: "error", message: response.message ?? "配置检查失败。" }); };

  return <motion.main key="config" className="page" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
    <SectionHeading kicker="CONFIGURATION" title="配置中心" detail="编辑 Agents、Tasks 和原始 JSON；保存前由 Python 验证实际工作流配置。" />
    <section className="metrics-row compact"><Metric label="Agents" value={`${agents.length}`} /><Metric label="Tasks" value={`${tasks.length}`} /><Metric label="启用任务" value={`${tasks.filter((task) => task.enabled).length}`} /><Metric label="当前状态" value={locked ? "运行中已锁定" : "可编辑"} tone={locked ? "running" : "succeeded"} /></section>
    <section className="panel config-workspace"><div className="tabs" role="tablist">{(["agents", "tasks", "json", "validation"] as ConfigTab[]).map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)} role="tab">{{ agents: "Agents", tasks: "Tasks", json: "JSON 高级编辑", validation: "配置检查" }[item]}</button>)}</div>
      {tab === "agents" && <><AgentTable rows={agents} onChange={setAgents} /><div className="sticky-actions"><button className="button secondary" disabled={locked} onClick={() => setAgents([...agents, { id: "new_agent", role: "新角色", goal: "", backstory: "", enabled: true }])}><Plus size={17} /> 新增 Agent</button><button className="button primary" disabled={locked} onClick={() => void save("agents", agents)}><Save size={17} /> 保存 Agents</button></div></>}
      {tab === "tasks" && <><TaskTable rows={tasks} agents={agents} onChange={setTasks} /><div className="sticky-actions"><button className="button secondary" disabled={locked} onClick={() => setTasks([...tasks, { id: "new_task", name: "新任务", description: "", expected_output: "", agent_id: agents[0]?.id ?? "", context_task_ids: [], enabled: true }])}><Plus size={17} /> 新增 Task</button><button className="button primary" disabled={locked} onClick={() => void save("tasks", tasks)}><Save size={17} /> 保存 Tasks</button></div></>}
      {tab === "json" && <><div className="json-grid"><label>Agents JSON<textarea className="code-editor" disabled={locked} value={agentsJson} onChange={(event) => setAgentsJson(event.target.value)} /></label><label>Tasks JSON<textarea className="code-editor" disabled={locked} value={tasksJson} onChange={(event) => setTasksJson(event.target.value)} /></label></div><div className="sticky-actions"><button className="button secondary" disabled={locked} onClick={() => { setAgentsJson(snapshot.config.agentsJson); setTasksJson(snapshot.config.tasksJson); }}><RefreshCw size={17} /> 重新读取</button><button className="button primary" disabled={locked} onClick={() => void saveJson()}><Save size={17} /> 保存 JSON</button></div></>}
      {tab === "validation" && <div className="validation-panel"><div><CheckCircle2 size={24} /><h3>配置检查</h3><p>校验启用 Agent、任务依赖和字段完整性。</p></div><button className="button primary" disabled={locked} onClick={() => void validate()}>立即检查</button><pre>{validation}</pre></div>}
    </section>
  </motion.main>;
}

function HistoryPage({ snapshot, bridge, onNotice }: { snapshot: AppSnapshot; bridge: StudioBridge; onNotice: (notice: Notice) => void }) {
  const [selected, setSelected] = useState<string | null>(snapshot.history[0]?.id ?? null);
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [tab, setTab] = useState<"summary" | "full" | "metadata">("summary");
  useEffect(() => { if (selected) void load(selected); }, [selected]);
  const load = async (id: string) => { const response = await bridge.loadHistory(id); if (response.ok && response.data) setDetail(response.data); else onNotice({ kind: "error", message: response.message ?? "读取历史记录失败。" }); };
  return <motion.main key="history" className="page" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
    <SectionHeading kicker="RUN HISTORY" title="历史输出" detail="回看已归档的报告、元数据和模型运行信息。" action={<button className="button ghost" onClick={() => void bridge.openLocation("outputs")}><FolderOpen size={17} /> 输出目录</button>} />
    <section className="history-layout"><aside className="panel history-list"><div className="panel-head"><h3>运行记录</h3><span>{snapshot.history.length}</span></div>{snapshot.history.length === 0 && <div className="empty-state">还没有历史运行。</div>}<div className="history-items">{snapshot.history.map((item) => <button key={item.id} className={item.id === selected ? "history-item active" : "history-item"} onClick={() => setSelected(item.id)}><span className={statusClass(item.status)}>{item.status === "failed" ? "失败" : "完成"}</span><strong>{item.createdAt}</strong><small>{item.modelAlias} · {formatSeconds(item.elapsedSeconds)}</small></button>)}</div></aside>
      <article className="panel history-detail"><div className="panel-head"><div><span className="eyebrow">REPORT DETAIL</span><h3>报告详情</h3></div>{selected && <button className="button ghost" onClick={() => void bridge.openLocation("history", selected)}><FolderOpen size={16} /> 打开目录</button>}</div><div className="tabs compact" role="tablist">{(["summary", "full", "metadata"] as const).map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{({ summary: "精简报告", full: "完整报告", metadata: "元数据" })[item]}</button>)}</div><div className="markdown report-content">{detail ? tab === "metadata" ? <pre>{detail.metadata}</pre> : <ReactMarkdown>{tab === "summary" ? detail.summary : detail.fullReport}</ReactMarkdown> : <div className="empty-state">选择一条运行记录查看内容。</div>}</div></article>
    </section>
  </motion.main>;
}

export default function App() {
  const [bridge, setBridge] = useState<StudioBridge | null>(null);
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [runState, setRunState] = useState<RunState | null>(null);
  const [page, setPage] = useState<Page>("run");
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => {
    let dispose: () => void = () => {};
    void getBridge().then(async (nextBridge) => {
      const response = await nextBridge.bootstrap();
      if (!response.ok || !response.data) { setNotice({ kind: "error", message: response.message ?? "无法初始化界面。" }); return; }
      setBridge(nextBridge); setSnapshot(response.data); setRunState(response.data.runState);
      const unsubscribers = [
        nextBridge.onRunState(setRunState),
        nextBridge.onHistory((history) => setSnapshot((current) => current ? { ...current, history } : current)),
        nextBridge.onNotice(setNotice)
      ];
      dispose = () => unsubscribers.forEach((unsubscribe) => unsubscribe());
    });
    return () => dispose();
  }, []);

  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(null), 4200); return () => window.clearTimeout(timer); }, [notice]);
  const applyConfig = (config: ConfigSnapshot) => setSnapshot((current) => current ? { ...current, config } : current);

  if (!snapshot || !runState || !bridge) return <div className="loading-screen"><LoaderCircle className="spin" size={28} /><span>正在连接本地工作台…</span></div>;
  const navigation = [{ id: "run" as const, label: "工作台", icon: LayoutDashboard }, { id: "config" as const, label: "配置中心", icon: Settings2 }, { id: "history" as const, label: "历史输出", icon: History }];

  return <MotionConfig reducedMotion="user" transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}><div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark"><Sparkles size={18} /></span><div><strong>Multiagent</strong><small>STUDIO</small></div></div><nav>{navigation.map((item) => { const Icon = item.icon; return <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => setPage(item.id)} disabled={false}><Icon size={19} /><span>{item.label}</span></button>; })}</nav><div className="sidebar-foot"><span className={statusClass(runState.status)}>{statusLabels[runState.status]}</span><small>本地工作流 · 离线界面</small></div></aside><div className="app-content"><AnimatePresence mode="wait">{page === "run" && <RunPage snapshot={snapshot} state={runState} bridge={bridge} onNotice={setNotice} />}{page === "config" && <ConfigPage snapshot={snapshot} state={runState} bridge={bridge} onConfig={applyConfig} onNotice={setNotice} />}{page === "history" && <HistoryPage snapshot={snapshot} bridge={bridge} onNotice={setNotice} />}</AnimatePresence></div><AnimatePresence>{notice && <motion.div className={`toast toast-${notice.kind}`} role="status" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }}>{notice.kind === "error" || notice.kind === "warning" ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}<span>{notice.message}</span></motion.div>}</AnimatePresence></div></MotionConfig>;
}
