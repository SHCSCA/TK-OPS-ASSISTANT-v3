import type { TaskInfo, TaskStatus } from "@/types/task-events";
import type { WorkspaceAICommandResultDto } from "@/types/runtime";

type FeedbackTone = "brand" | "danger" | "success" | "warning";

export type WorkspaceCommandFeedbackViewModel = {
  canCancel: boolean;
  canRetry: boolean;
  detail: string;
  icon: string;
  progress: number;
  showProgress: boolean;
  spinning: boolean;
  status: TaskStatus;
  taskId: string;
  title: string;
  tone: FeedbackTone;
};

export function buildWorkspaceCommandFeedback(
  activeTask: TaskInfo | null,
  lastCommandResult: WorkspaceAICommandResultDto | null
): WorkspaceCommandFeedbackViewModel | null {
  if (activeTask) {
    return buildTaskFeedback(activeTask);
  }

  if (!lastCommandResult || lastCommandResult.status === "blocked") {
    return null;
  }

  return buildResultFeedback(lastCommandResult);
}

function buildTaskFeedback(task: TaskInfo): WorkspaceCommandFeedbackViewModel {
  const progress = clampProgress(task.progress);
  return {
    canCancel: task.status === "queued" || task.status === "running",
    canRetry: false,
    detail: task.message || "AI 命令正在通过 TaskBus 执行。",
    icon: task.status === "queued" ? "pending" : "sync",
    progress,
    showProgress: true,
    spinning: task.status === "running",
    status: task.status,
    taskId: task.id,
    title: task.status === "queued" ? "智能粗剪排队中" : "智能粗剪处理中",
    tone: "brand"
  };
}

function buildResultFeedback(result: WorkspaceAICommandResultDto): WorkspaceCommandFeedbackViewModel {
  const task = result.task;
  const taskId = task?.id ?? "";
  const progress = clampProgress(task?.progress ?? (result.status === "succeeded" ? 100 : 0));
  const titleByStatus: Record<Exclude<WorkspaceAICommandResultDto["status"], "blocked">, string> = {
    cancelled: "智能粗剪已取消",
    cancelling: "正在取消智能粗剪",
    failed: "智能粗剪失败",
    queued: "智能粗剪排队中",
    running: "智能粗剪处理中",
    succeeded: "智能粗剪完成"
  };
  const toneByStatus: Record<Exclude<WorkspaceAICommandResultDto["status"], "blocked">, FeedbackTone> = {
    cancelled: "warning",
    cancelling: "warning",
    failed: "danger",
    queued: "brand",
    running: "brand",
    succeeded: "success"
  };
  const iconByStatus: Record<Exclude<WorkspaceAICommandResultDto["status"], "blocked">, string> = {
    cancelled: "pause_circle",
    cancelling: "stop_circle",
    failed: "error",
    queued: "pending",
    running: "sync",
    succeeded: "check_circle"
  };

  return {
    canCancel: Boolean(taskId) && (result.status === "queued" || result.status === "running"),
    canRetry: result.status === "failed" || result.status === "cancelled",
    detail: result.message || task?.message || "AI 命令状态已更新。",
    icon: iconByStatus[result.status],
    progress,
    showProgress: result.status === "queued" || result.status === "running",
    spinning: result.status === "running",
    status: result.status,
    taskId,
    title: titleByStatus[result.status],
    tone: toneByStatus[result.status]
  };
}

function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}
