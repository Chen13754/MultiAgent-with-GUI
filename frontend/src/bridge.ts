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

type Listener<T> = (value: T) => void;
type Unsubscribe = () => void;

export interface StudioBridge {
  bootstrap(): Promise<ApiResponse<AppSnapshot>>;
  startRun(topic: string, model: string): Promise<ApiResponse<{ accepted: boolean }>>;
  resetRun(): Promise<ApiResponse<RunState>>;
  validateConfig(): Promise<ApiResponse<{ text: string }>>;
  saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[]): Promise<ApiResponse<ConfigSnapshot>>;
  saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[]): Promise<ApiResponse<ConfigSnapshot>>;
  loadHistory(id: string): Promise<ApiResponse<HistoryDetail>>;
  openLocation(target: "outputs" | "history", id?: string): Promise<ApiResponse<unknown>>;
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

function subscribe<T>(signal: ChannelSignal, listener: Listener<T>): Unsubscribe {
  const callback = (json: string) => {
    try {
      listener(JSON.parse(json) as T);
    } catch {
      // Ignore a malformed notification; the next full state will recover the UI.
    }
  };
  signal.connect(callback);
  return () => signal.disconnect(callback);
}

class QtChannelBridge implements StudioBridge {
  constructor(private readonly studio: ChannelObject) {}

  private invoke<T>(method: string, ...args: unknown[]): Promise<ApiResponse<T>> {
    return new Promise((resolve) => {
      this.studio[method](...args, (result: unknown) => resolve(decode<T>(String(result))));
    });
  }

  bootstrap() { return this.invoke<AppSnapshot>("bootstrap"); }
  startRun(topic: string, model: string) { return this.invoke<{ accepted: boolean }>("startRun", topic, model); }
  resetRun() { return this.invoke<RunState>("resetRun"); }
  validateConfig() { return this.invoke<{ text: string }>("validateConfig"); }
  saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[]) {
    return this.invoke<ConfigSnapshot>("saveConfig", kind, JSON.stringify(payload));
  }
  saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[]) {
    return this.invoke<ConfigSnapshot>("saveConfigBundle", JSON.stringify(agents), JSON.stringify(tasks));
  }
  loadHistory(id: string) { return this.invoke<HistoryDetail>("loadHistory", id); }
  openLocation(target: "outputs" | "history", id = "") { return this.invoke("openLocation", target, id); }
  onRunState(listener: Listener<RunState>) { return subscribe(this.studio.runStateChanged, listener); }
  onHistory(listener: Listener<HistoryItem[]>) { return subscribe(this.studio.historyChanged, listener); }
  onNotice(listener: Listener<Notice>) { return subscribe(this.studio.noticeRaised, listener); }
}

const demoAgents: AgentConfig[] = [
  { id: "problem_analyst", role: "问题分析师", goal: "梳理问题、约束和成功标准", backstory: "善于把模糊问题拆成清晰结构。", enabled: true },
  { id: "solution_strategist", role: "方案策略师", goal: "形成可执行的解决方案", backstory: "在多种方案间权衡可行性。", enabled: true }
];

const demoTasks: TaskConfig[] = [
  { id: "analysis", name: "问题分析", description: "分析 {topic}", expected_output: "结构化问题分析", agent_id: "problem_analyst", context_task_ids: [], enabled: true },
  { id: "solution", name: "方案设计", description: "基于分析制定方案", expected_output: "可执行方案", agent_id: "solution_strategist", context_task_ids: ["analysis"], enabled: true }
];

function initialState(): RunState {
  return { status: "idle", progress: 0, modelAlias: "flash", topic: "", taskCount: 2, activeAgent: "等待启动", events: [], result: null, error: null };
}

class MockBridge implements StudioBridge {
  private state = initialState();
  private history: HistoryItem[] = [];
  private agents = demoAgents;
  private tasks = demoTasks;
  private stateListeners = new Set<Listener<RunState>>();
  private historyListeners = new Set<Listener<HistoryItem[]>>();
  private noticeListeners = new Set<Listener<Notice>>();

  private config(): ConfigSnapshot {
    return {
      agents: this.agents,
      tasks: this.tasks,
      agentsJson: JSON.stringify(this.agents, null, 2),
      tasksJson: JSON.stringify(this.tasks, null, 2),
      enabledTaskCount: this.tasks.filter((task) => task.enabled).length,
      validationText: "配置检查通过。前端开发模式使用本地模拟数据。"
    };
  }

  private emitState() { this.stateListeners.forEach((listener) => listener({ ...this.state })); }
  private emitHistory() { this.historyListeners.forEach((listener) => listener([...this.history])); }
  private notice(notice: Notice) { this.noticeListeners.forEach((listener) => listener(notice)); }

  async bootstrap(): Promise<ApiResponse<AppSnapshot>> {
    return { ok: true, data: { models: ["flash", "pro"], defaultModel: "flash", apiKeyConfigured: { flash: true, pro: true }, config: this.config(), history: this.history, runState: this.state } };
  }

  async startRun(topic: string, model: string): Promise<ApiResponse<{ accepted: boolean }>> {
    if (this.state.status === "running") return { ok: false, code: "run_active", message: "工作流正在运行。" };
    this.state = { ...initialState(), status: "running", modelAlias: model, topic, taskCount: this.tasks.filter((task) => task.enabled).length, progress: 5, activeAgent: "问题分析师" };
    this.emitState();
    const events = [
      { type: "run_started", agent: "问题分析师" },
      { type: "task_completed", agent: "问题分析师" },
      { type: "task_completed", agent: "方案策略师" }
    ];
    events.forEach((event, index) => window.setTimeout(() => {
      this.state = { ...this.state, events: [...this.state.events, event], activeAgent: String(event.agent), progress: Math.min(95, 10 + (index + 1) * 35) };
      this.emitState();
    }, 650 * (index + 1)));
    window.setTimeout(() => {
      const record: HistoryItem = { id: `demo:${Date.now()}`, createdAt: new Date().toISOString().replace(/[TZ]/g, " ").slice(0, 19), modelAlias: model, elapsedSeconds: 2.1, status: "succeeded" };
      this.history = [record, ...this.history];
      this.state = {
        ...this.state,
        status: "succeeded",
        progress: 100,
        result: { historyId: record.id, modelAlias: model, elapsedSeconds: 2.1, summary: `已完成“${topic || "默认主题"}”的多 Agent 协作。`, fullReport: `# 完整报告\n\n围绕 **${topic || "默认主题"}** 生成了分析与方案。`, taskOutputs: [{ agent: "问题分析师", output: "已完成问题拆解。" }, { agent: "方案策略师", output: "已完成方案建议。" }] }
      };
      this.emitState();
      this.emitHistory();
      this.notice({ kind: "success", message: "开发模式：模拟工作流已完成。" });
    }, 2650);
    return { ok: true, data: { accepted: true } };
  }

  async resetRun() { this.state = initialState(); this.emitState(); return { ok: true, data: this.state }; }
  async validateConfig() { return { ok: true, data: { text: this.config().validationText } }; }
  async saveConfig(kind: "agents" | "tasks", payload: AgentConfig[] | TaskConfig[]) {
    if (kind === "agents") this.agents = payload as AgentConfig[];
    else this.tasks = payload as TaskConfig[];
    return { ok: true, data: this.config() };
  }
  async saveConfigBundle(agents: AgentConfig[], tasks: TaskConfig[]) {
    this.agents = agents;
    this.tasks = tasks;
    return { ok: true, data: this.config() };
  }
  async loadHistory(id: string) { return { ok: true, data: { id, summary: "模拟历史摘要", fullReport: "# 模拟历史报告\n\n可在桌面应用中读取真实归档。", metadata: "- 模型档位：flash\n- 总用时：2.10 秒" } }; }
  async openLocation() { return { ok: true }; }
  onRunState(listener: Listener<RunState>) { this.stateListeners.add(listener); return () => this.stateListeners.delete(listener); }
  onHistory(listener: Listener<HistoryItem[]>) { this.historyListeners.add(listener); return () => this.historyListeners.delete(listener); }
  onNotice(listener: Listener<Notice>) { this.noticeListeners.add(listener); return () => this.noticeListeners.delete(listener); }
}

let bridgePromise: Promise<StudioBridge> | undefined;

export function getBridge(): Promise<StudioBridge> {
  if (bridgePromise) return bridgePromise;
  bridgePromise = new Promise((resolve) => {
    if (window.qt?.webChannelTransport && window.QWebChannel) {
      new window.QWebChannel(window.qt.webChannelTransport, (channel) => resolve(new QtChannelBridge(channel.objects.studio)));
      return;
    }
    resolve(new MockBridge());
  });
  return bridgePromise;
}
