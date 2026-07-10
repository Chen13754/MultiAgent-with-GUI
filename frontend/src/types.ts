export type RunStatus = "idle" | "running" | "succeeded" | "failed";

export interface AgentConfig {
  id: string;
  role: string;
  goal: string;
  backstory: string;
  enabled: boolean;
}

export interface TaskConfig {
  id: string;
  name: string;
  description: string;
  expected_output: string;
  agent_id: string;
  context_task_ids: string[];
  enabled: boolean;
}

export interface TaskOutput {
  agent?: string;
  task_id?: string;
  task_name?: string;
  description?: string;
  output: string;
}

export interface RunResult {
  historyId: string;
  modelAlias: string;
  elapsedSeconds: number;
  summary: string;
  fullReport: string;
  taskOutputs: TaskOutput[];
}

export interface RunState {
  status: RunStatus;
  progress: number;
  modelAlias: string;
  topic: string;
  taskCount: number;
  activeAgent: string;
  events: Array<Record<string, unknown>>;
  result: RunResult | null;
  error: string | null;
}

export interface ConfigSnapshot {
  agents: AgentConfig[];
  tasks: TaskConfig[];
  agentsJson: string;
  tasksJson: string;
  enabledTaskCount: number;
  validationText: string;
}

export interface HistoryItem {
  id: string;
  createdAt: string;
  modelAlias: string;
  elapsedSeconds: number | null;
  status: "succeeded" | "failed";
}

export interface HistoryDetail {
  id: string;
  summary: string;
  fullReport: string;
  metadata: string;
}

export interface AppSnapshot {
  models: string[];
  defaultModel: string;
  apiKeyConfigured: Record<string, boolean>;
  config: ConfigSnapshot;
  history: HistoryItem[];
  runState: RunState;
}

export interface Notice {
  kind: "success" | "error" | "warning" | "info";
  message: string;
}

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  code?: string;
  message?: string;
}
