export type TaskEventType =
  | "task.started"
  | "task.progress"
  | "task.log"
  | "task.completed"
  | "task.failed";

export type TaskStatus =
  | "queued"
  | "running"
  | "blocked"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface TaskEvent {
  schema_version: number;
  type: TaskEventType;
  taskId: string;
  taskType: string;
  projectId: string | null;
  status: TaskStatus;
  progress: number;
  message: string;
}

export interface TaskInfo {
  id: string;
  status: TaskStatus;
  kind?: string;
  label?: string;
  progressPct?: number | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  etaMs?: number | null;
  projectId?: string | null;
  ownerRef?: { kind: string; id: string } | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  retryable?: boolean;
  createdAt?: string;
  updatedAt?: string;
  task_type?: string;
  project_id?: string | null;
  progress?: number;
  message?: string;
  created_at?: string;
  updated_at?: string;
}
