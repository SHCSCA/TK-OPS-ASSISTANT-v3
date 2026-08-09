import { getAccountTask } from "./tasks";
import { RuntimeError } from "./core";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

export async function waitForAccountTask(
  accountId: string,
  taskId: string,
  options: {
    signal: AbortSignal;
    timeoutMs: number;
    pollIntervalMs?: number;
    failureMessage?: string;
  }
): Promise<RuntimeTaskDto> {
  const deadline = Date.now() + options.timeoutMs;
  while (!options.signal.aborted && Date.now() < deadline) {
    let result;
    try {
      result = await getAccountTask(accountId, taskId, {
        signal: options.signal
      });
    } catch (error) {
      if (
        options.signal.aborted
        || !(error instanceof RuntimeError)
        || !["RUNTIME_CONNECTION_CHANGED", "RUNTIME_NOT_READY"].includes(
          error.errorCode
        )
      ) {
        throw error;
      }
      await abortableDelay(options.pollIntervalMs ?? 800, options.signal);
      continue;
    }
    const task = result.data;
    if (task.status === "completed" && task.completionKind === "succeeded") {
      return task;
    }
    if (task.status === "failed" || task.completionKind === "cancelled") {
      throw new RuntimeError(
        task.completionKind === "cancelled"
          ? "任务已取消。"
          : options.failureMessage ?? "任务执行失败。",
        {
          errorCode: task.errorCode ?? "TASK_STATE_CONFLICT",
          logId: task.logId,
          status: 409
        }
      );
    }
    await abortableDelay(options.pollIntervalMs ?? 800, options.signal);
  }
  if (options.signal.aborted) {
    throw new DOMException("任务轮询已取消", "AbortError");
  }
  throw new RuntimeError("等待任务完成超时，请查看任务日志。", {
    errorCode: "TASK_TIMEOUT",
    status: 408
  });
}

function abortableDelay(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, milliseconds);
    signal.addEventListener("abort", () => {
      window.clearTimeout(timer);
      reject(new DOMException("任务轮询已取消", "AbortError"));
    }, { once: true });
  });
}
