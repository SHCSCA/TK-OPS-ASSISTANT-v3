export type TaskEventType =
  | "task.started"
  | "task.progress"
  | "task.log"
  | "task.completed"
  | "task.failed"
  | "script.ai.stream.chunk"
  | "script.ai.stream.completed"
  | "script.ai.stream.failed"
  | "video.import.stage.started"
  | "video.import.stage.progress"
  | "video.import.stage.completed"
  | "video.import.stage.failed"
  | "render.progress"
  | "account.status.changed"
  | "device.status.changed"
  | "publish.receipt.updated";

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
  taskId?: string;
  taskType?: string;
  projectId?: string | null;
  status?: TaskStatus;
  progress?: number;
  progressPct?: number;
  message?: string;
  videoId?: string;
  stage?: string;
  startedAt?: string;
  resultSummary?: string;
  errorCode?: string | null;
  errorMessage?: string | null;
  jobId?: string;
  sequence?: number;
  deltaText?: string;
  fullText?: string;
  versionId?: string;
  trackId?: string;
  bitrateKbps?: number;
  outputSec?: number;
  accountId?: string;
  lastSyncedAt?: string | null;
  workspaceId?: string;
  lastSeenAt?: string | null;
  planId?: string;
  platformResponse?: unknown;
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
