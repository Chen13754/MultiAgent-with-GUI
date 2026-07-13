import type {
  AgentConfig,
  ApiResponse,
  AppSnapshot,
  ConfigSnapshot,
  HistoryDetail,
  HistoryItem,
  Notice,
  RunState,
  TaskConfig
} from "./types";

const PROTOCOL_VERSION = 2;
type Listener<T> = (value: T) => void;
type Unsubscribe = () => void;

export interface StudioBridge {
  bootstrap(): Promise<ApiResponse<AppSnapshot>>;
  startRun(topic: string, model: string): Promise<ApiResponse<{ accepted: boolean; runId: string }>>;
  cancelRun(): Promise<ApiResponse<{ accepted: boolean }>>;
  resetRun(): Promise<ApiResponse<RunState>>;
  validateConfig(): Promise<ApiResponse<{ text: string }>>;
  saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[], baseRevision?: string): Promise<ApiResponse<ConfigSnapshot>>;
  saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[], baseRevision?: string): Promise<ApiResponse<ConfigSnapshot>>;
  saveGraph(graph: ConfigSnapshot["graph"], baseRevision?: string): Promise<ApiResponse<ConfigSnapshot>>;
  resetConfig(): Promise<ApiResponse<AppSnapshot>>;
  saveApiKey(key: string): Promise<ApiResponse<{ configured: boolean; envFile: string }>>;
  exportDiagnostics(): Promise<ApiResponse<{ path: string }>>;
  loadHistory(id: string): Promise<ApiResponse<HistoryDetail>>;
  openLocation(target: "outputs" | "history" | "config", id?: string): Promise<ApiResponse<unknown>>;
  onRunState(listener: Listener<RunState>): Unsubscribe;
  onHistory(listener: Listener<HistoryItem[]>): Unsubscribe;
  onNotice(listener: Listener<Notice>): Unsubscribe;
}

type ChannelSignal = { connect(callback: (json: string) => void): void; disconnect(callback: (json: string) => void): void };
type ChannelObject = Record<string, (...args: unknown[]) => void> & {
  runStateChanged: ChannelSignal;
  historyChanged: ChannelSignal;
  noticeRaised: ChannelSignal;
};

declare global {
  interface Window {
    qt?: { webChannelTransport: unknown };
    QWebChannel?: new (transport: unknown, ready: (channel: { objects: { studio: ChannelObject } }) => void) => unknown;
  }
}

function decode<T>(value: string): ApiResponse<T> {
  try {
    return JSON.parse(value) as ApiResponse<T>;
  } catch {
    return { ok: false, code: "bridge_decode", message: "桌面通信返回了无效数据。" };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function isGraphLayout(value: unknown): value is ConfigSnapshot["graph"] {
  if (!isRecord(value) || !isRecord(value.positions) || !isRecord(value.viewport)) return false;
  const viewport = value.viewport;
  return typeof viewport.x === "number" && Number.isFinite(viewport.x)
    && typeof viewport.y === "number" && Number.isFinite(viewport.y)
    && typeof viewport.zoom === "number" && Number.isFinite(viewport.zoom)
    && Object.values(value.positions).every((position) => isRecord(position)
      && typeof position.x === "number" && Number.isFinite(position.x)
      && typeof position.y === "number" && Number.isFinite(position.y));
}

function isConfigSnapshot(value: unknown): value is ConfigSnapshot {
  if (!isRecord(value)) return false;
  return Array.isArray(value.agents)
    && Array.isArray(value.tasks)
    && isGraphLayout(value.graph)
    && typeof value.revision === "string"
    && typeof value.agentsJson === "string"
    && typeof value.tasksJson === "string"
    && typeof value.enabledTaskCount === "number"
    && typeof value.validationText === "string";
}

function isRunState(value: unknown): value is RunState {
  if (!isRecord(value) || !Array.isArray(value.events) || !isRecord(value.taskStates)) return false;
  return typeof value.status === "string" && typeof value.runId === "string"
    && typeof value.progress === "number" && typeof value.modelAlias === "string"
    && typeof value.topic === "string" && typeof value.taskCount === "number"
    && typeof value.activeAgent === "string";
}

function isNotice(value: unknown): value is Notice {
  return isRecord(value) && typeof value.kind === "string" && typeof value.message === "string";
}

function isAppSnapshot(value: unknown): value is AppSnapshot {
  if (!isRecord(value)) return false;
  const row = value;
  const config = row.config;
  return row.protocolVersion === PROTOCOL_VERSION
    && Array.isArray(row.models)
    && typeof row.defaultModel === "string"
    && isConfigSnapshot(config)
    && Array.isArray(row.history)
    && isRunState(row.runState);
}

function subscribe<T>(signal: ChannelSignal, listener: Listener<T>, guard?: (value: unknown) => value is T): Unsubscribe {
  const callback = (json: string) => {
    try {
      const value: unknown = JSON.parse(json);
      if (!guard || guard(value)) listener(value as T);
    } catch { /* A later full state can recover. */ }
  };
  signal.connect(callback);
  return () => signal.disconnect(callback);
}

function configResponse(response: ApiResponse<ConfigSnapshot>): ApiResponse<ConfigSnapshot> {
  if (response.ok && !isConfigSnapshot(response.data)) {
    return { ok: false, code: "protocol_mismatch", message: "桌面配置响应不符合当前协议。" };
  }
  return response;
}

class QtChannelBridge implements StudioBridge {
  constructor(private readonly studio: ChannelObject) {}

  private invoke<T>(method: string, ...args: unknown[]): Promise<ApiResponse<T>> {
    return new Promise((resolve) => {
      const target = this.studio?.[method];
      if (typeof target !== "function") {
        resolve({ ok: false, code: "bridge_method_missing", message: `桌面后端缺少方法：${method}` });
        return;
      }
      target(...args, (result: unknown) => resolve(decode<T>(String(result))));
    });
  }

  async bootstrap() {
    const response = await this.invoke<AppSnapshot>("bootstrap");
    if (response.ok && !isAppSnapshot(response.data)) {
      return { ok: false, code: "protocol_mismatch", message: "桌面前后端协议版本不兼容。" };
    }
    return response;
  }
  startRun(topic: string, model: string) { return this.invoke<{ accepted: boolean; runId: string }>("startRun", topic, model); }
  cancelRun() { return this.invoke<{ accepted: boolean }>("cancelRun"); }
  resetRun() { return this.invoke<RunState>("resetRun"); }
  validateConfig() { return this.invoke<{ text: string }>("validateConfig"); }
  saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[], baseRevision = "") {
    return this.invoke<ConfigSnapshot>("saveConfig", kind, JSON.stringify(payload), baseRevision).then(configResponse);
  }
  saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[], baseRevision = "") {
    return this.invoke<ConfigSnapshot>("saveConfigBundle", JSON.stringify(agents), JSON.stringify(tasks), baseRevision).then(configResponse);
  }
  saveGraph(graph: ConfigSnapshot["graph"], baseRevision = "") {
    return this.invoke<ConfigSnapshot>("saveGraph", JSON.stringify(graph), baseRevision).then(configResponse);
  }
  resetConfig() { return this.invoke<AppSnapshot>("resetConfig"); }
  saveApiKey(key: string) { return this.invoke<{ configured: boolean; envFile: string }>("saveApiKey", key); }
  exportDiagnostics() { return this.invoke<{ path: string }>("exportDiagnostics"); }
  loadHistory(id: string) { return this.invoke<HistoryDetail>("loadHistory", id); }
  openLocation(target: "outputs" | "history" | "config", id = "") { return this.invoke("openLocation", target, id); }
  onRunState(listener: Listener<RunState>) { return subscribe(this.studio.runStateChanged, listener, isRunState); }
  onHistory(listener: Listener<HistoryItem[]>) { return subscribe(this.studio.historyChanged, listener, (value): value is HistoryItem[] => Array.isArray(value)); }
  onNotice(listener: Listener<Notice>) { return subscribe(this.studio.noticeRaised, listener, isNotice); }
}

const demoAgents: AgentConfig[] = [
  { id: "problem_analyst", role: "问题分析师", goal: "梳理问题", backstory: "结构化分析", enabled: true },
  { id: "solution_strategist", role: "方案策略师", goal: "形成方案", backstory: "务实设计", enabled: true }
];
const demoTasks: TaskConfig[] = [
  { id: "analysis", name: "问题分析", description: "分析 {topic}", expected_output: "结构化分析", agent_id: "problem_analyst", context_task_ids: [], artifact_role: "full_report", enabled: true },
  { id: "summary", name: "精简总结", description: "总结结果", expected_output: "精简报告", agent_id: "solution_strategist", context_task_ids: ["analysis"], artifact_role: "summary", enabled: true }
];
const demoGraph: ConfigSnapshot["graph"] = {
  positions: { analysis: { x: 40, y: 90 }, summary: { x: 310, y: 90 } },
  viewport: { x: 0, y: 0, zoom: 1 }
};

function initialState(): RunState {
  return { status: "idle", runId: "", progress: 0, modelAlias: "flash", topic: "", taskCount: 2, activeAgent: "等待启动", events: [], taskStates: {}, result: null, error: null };
}

class MockBridge implements StudioBridge {
  private state = initialState();
  private history: HistoryItem[] = [];
  private agents = demoAgents;
  private tasks = demoTasks;
  private graph = demoGraph;
  private stateListeners = new Set<Listener<RunState>>();
  private historyListeners = new Set<Listener<HistoryItem[]>>();
  private noticeListeners = new Set<Listener<Notice>>();
  private timers: number[] = [];
  private config(): ConfigSnapshot { return { agents: this.agents, tasks: this.tasks, graph: this.graph, revision: "demo", agentsJson: JSON.stringify(this.agents, null, 2), tasksJson: JSON.stringify(this.tasks, null, 2), enabledTaskCount: this.tasks.filter((task) => task.enabled).length, validationText: "开发模式模拟配置。" }; }
  private snapshot(): AppSnapshot { return { protocolVersion: PROTOCOL_VERSION, models: ["flash", "pro"], defaultModel: "flash", apiKeyConfigured: { flash: true, pro: true }, configPath: "development/mock", envFile: "development/mock/.env", config: this.config(), history: this.history, runState: this.state }; }
  private emitState() { this.stateListeners.forEach((listener) => listener({ ...this.state })); }
  private emitHistory() { this.historyListeners.forEach((listener) => listener([...this.history])); }
  private notice(notice: Notice) { this.noticeListeners.forEach((listener) => listener(notice)); }
  async bootstrap(): Promise<ApiResponse<AppSnapshot>> { return { ok: true, data: this.snapshot() }; }
  async startRun(topic: string, model: string): Promise<ApiResponse<{ accepted: boolean; runId: string }>> {
    if (this.state.status === "running") return { ok: false, code: "run_active", message: "工作流正在运行。" };
    const runId = `demo-${Date.now()}`;
    this.state = { ...initialState(), status: "running", runId, modelAlias: model, topic, taskCount: this.tasks.filter((task) => task.enabled).length, progress: 5, activeAgent: "问题分析师" };
    this.emitState();
    this.tasks.forEach((task, index) => this.timers.push(window.setTimeout(() => {
      const event = { type: "task_completed", task_id: task.id, task_name: task.name, agent: task.agent_id };
      this.state = { ...this.state, events: [...this.state.events, event], activeAgent: task.name, progress: Math.min(95, 10 + (index + 1) * 40) };
      this.emitState();
    }, 450 * (index + 1))));
    this.timers.push(window.setTimeout(() => {
      const record: HistoryItem = { id: runId, createdAt: new Date().toISOString(), modelAlias: model, elapsedSeconds: 1.4, status: "succeeded" };
      this.history = [record, ...this.history];
      this.state = { ...this.state, status: "succeeded", progress: 100, result: { historyId: record.id, modelAlias: model, elapsedSeconds: 1.4, summary: `已完成“${topic || "默认主题"}”。`, fullReport: `# 开发模式报告\n\n${topic}`, taskOutputs: [] } };
      this.emitState(); this.emitHistory(); this.notice({ kind: "success", message: "开发模式模拟运行已完成。" });
    }, 1500));
    return { ok: true, data: { accepted: true, runId } };
  }
  async cancelRun() { this.timers.forEach(window.clearTimeout); this.timers = []; this.state = { ...this.state, status: "cancelled", progress: 0 }; this.emitState(); return { ok: true, data: { accepted: true } }; }
  async resetRun() { this.state = initialState(); this.emitState(); return { ok: true, data: this.state }; }
  async validateConfig() { return { ok: true, data: { text: this.config().validationText } }; }
  async saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[], _baseRevision = "") { if (kind === "agents") this.agents = payload as AgentConfig[]; else this.tasks = payload as TaskConfig[]; return { ok: true, data: this.config() }; }
  async saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[], _baseRevision = "") { this.agents = agents; this.tasks = tasks; return { ok: true, data: this.config() }; }
  async saveGraph(graph: ConfigSnapshot["graph"], _baseRevision = "") { this.graph = graph; return { ok: true, data: this.config() }; }
  async resetConfig() { this.agents = demoAgents; this.tasks = demoTasks; this.graph = demoGraph; return { ok: true, data: this.snapshot() }; }
  async saveApiKey() { return { ok: true, data: { configured: true, envFile: "development/mock/.env" } }; }
  async exportDiagnostics() { return { ok: true, data: { path: "development/mock/diagnostics.zip" } }; }
  async loadHistory(id: string) { return { ok: true, data: { id, summary: "模拟摘要", fullReport: "# 模拟报告", metadata: "开发模式" } }; }
  async openLocation() { return { ok: true }; }
  onRunState(listener: Listener<RunState>) { this.stateListeners.add(listener); return () => this.stateListeners.delete(listener); }
  onHistory(listener: Listener<HistoryItem[]>) { this.historyListeners.add(listener); return () => this.historyListeners.delete(listener); }
  onNotice(listener: Listener<Notice>) { this.noticeListeners.add(listener); return () => this.noticeListeners.delete(listener); }
}

class UnavailableBridge implements StudioBridge {
  private error<T>(): Promise<ApiResponse<T>> { return Promise.resolve({ ok: false, code: "desktop_bridge_unavailable", message: "桌面后端未连接。请重新安装或检查应用日志。" }); }
  bootstrap() { return this.error<AppSnapshot>(); }
  startRun() { return this.error<{ accepted: boolean; runId: string }>(); }
  cancelRun() { return this.error<{ accepted: boolean }>(); }
  resetRun() { return this.error<RunState>(); }
  validateConfig() { return this.error<{ text: string }>(); }
  saveConfig() { return this.error<ConfigSnapshot>(); }
  saveConfigBundle() { return this.error<ConfigSnapshot>(); }
  saveGraph() { return this.error<ConfigSnapshot>(); }
  resetConfig() { return this.error<AppSnapshot>(); }
  saveApiKey() { return this.error<{ configured: boolean; envFile: string }>(); }
  exportDiagnostics() { return this.error<{ path: string }>(); }
  loadHistory() { return this.error<HistoryDetail>(); }
  openLocation() { return this.error<unknown>(); }
  onRunState() { return () => {}; }
  onHistory() { return () => {}; }
  onNotice() { return () => {}; }
}

let bridgePromise: Promise<StudioBridge> | undefined;
export function getBridge(): Promise<StudioBridge> {
  if (bridgePromise) return bridgePromise;
  bridgePromise = new Promise((resolve) => {
    if (window.qt?.webChannelTransport && window.QWebChannel) {
      new window.QWebChannel(window.qt.webChannelTransport, (channel) => resolve(new QtChannelBridge(channel.objects.studio)));
      return;
    }
    resolve(import.meta.env.DEV ? new MockBridge() : new UnavailableBridge());
  });
  return bridgePromise;
}
