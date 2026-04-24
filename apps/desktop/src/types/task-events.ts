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
  | "video_status_changed"
  | "render.progress"
  | "render.status.changed"
  | "account.status.changed"
  | "device.status.changed"
  | "publishing.precheck.completed"
  | "publishing.submit.completed"
  | "publishing.receipt.updated"
  | "publish.receipt.updated"
  | "config.changed"
  | "ai-capability.changed";

export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

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

  // Fields for config.changed and ai-capability.changed
  scope?: string;
  revision?: number;
  updatedAt?: string;
  changedKeys?: string[];
  configVersion?: number;
  reason?: string;
  providerIds?: string[];
  capabilityIds?: string[];
}

export interface TaskInfo {
  id: string;
  task_type: string;
  project_id: string | null;
  status: TaskStatus;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface ConfigChangedEvent extends TaskEvent {
  type: "config.changed";
  scope: string;
  revision: number;
  updatedAt: string;
  changedKeys: string[];
}

export interface AICapabilityChangedEvent extends TaskEvent {
  type: "ai-capability.changed";
  scope: string;
  configVersion: number;
  reason: string;
  providerIds: string[];
  capabilityIds: string[];
}
