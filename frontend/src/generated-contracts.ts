// Generated from contracts/studio.schema.json. Do not edit by hand.

export type RunStatus = "idle" | "running" | "succeeded" | "failed" | "cancelled";

export type TaskStatus = "waiting" | "running" | "succeeded" | "failed" | "cancelled";

export type ArtifactRole = "none" | "full_report" | "summary";

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
  context_task_ids: Array<string>;
  artifact_role: ArtifactRole;
  enabled: boolean;
}

export interface GraphPosition {
  x: number;
  y: number;
}

export interface GraphViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface GraphLayout {
  positions: Record<string, GraphPosition>;
  viewport: GraphViewport;
}

export interface TaskOutput {
  agent?: string;
  task_id?: string;
  task_name?: string;
  artifact_role?: ArtifactRole;
  description?: string;
  output: string;
}

export interface RunResult {
  historyId: string;
  modelAlias: string;
  elapsedSeconds: number;
  summary: string;
  fullReport: string;
  taskOutputs: Array<TaskOutput>;
}

export interface RunState {
  status: RunStatus;
  runId: string;
  progress: number;
  modelAlias: string;
  topic: string;
  taskCount: number;
  activeAgent: string;
  events: Array<Record<string, unknown>>;
  taskStates: Record<string, TaskStatus>;
  result: RunResult | null;
  error: string | null;
}

export interface ConfigSnapshot {
  agents: Array<AgentConfig>;
  tasks: Array<TaskConfig>;
  graph: GraphLayout;
  revision: string;
  agentsJson: string;
  tasksJson: string;
  enabledTaskCount: number;
  validationText: string;
}

export type HistoryStatus = "succeeded" | "failed" | "cancelled" | "interrupted";

export interface HistoryItem {
  id: string;
  runId?: string;
  createdAt: string;
  modelAlias: string;
  elapsedSeconds: number | null;
  status: HistoryStatus;
}

export interface HistoryDetail {
  id: string;
  summary: string;
  fullReport: string;
  metadata: string;
}

export interface AppSnapshot {
  protocolVersion: number;
  models: Array<string>;
  defaultModel: string;
  apiKeyConfigured: Record<string, boolean>;
  configPath: string;
  envFile: string;
  config: ConfigSnapshot;
  history: Array<HistoryItem>;
  runState: RunState;
}

export interface Notice {
  kind: "success" | "error" | "warning" | "info";
  message: string;
}
