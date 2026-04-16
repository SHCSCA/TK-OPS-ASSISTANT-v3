export type TaskEventType =
  | "task.started"
  | "task.progress"
  | "task.log"
  | "task.completed"
  | "task.failed";

export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

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
  task_type: string;
  project_id: string | null;
  status: TaskStatus;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}
