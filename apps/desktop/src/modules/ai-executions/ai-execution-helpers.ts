import { RuntimeError } from "@/app/runtime-client/core";
import type {
  AIExecutionCompletionKind,
  AIExecutionFailureKind,
  AIExecutionStatus
} from "@/types/runtime/ai-executions";
import type { AIConfigUiError } from "@/modules/system/ai-config/ai-config-types";
import { toAIConfigUiError } from "@/modules/system/ai-config/ai-config-helpers";

export function executionStatusLabel(
  status: AIExecutionStatus,
  failureKind: AIExecutionFailureKind = null,
  completionKind: AIExecutionCompletionKind = null
): string {
  if (status === "queued") return "等待执行";
  if (status === "running") return "正在调用";
  if (status === "cancelling") return "正在取消";
  if (status === "completed") {
    return completionKind === "cancelled" ? "已取消" : "已完成";
  }
  if (failureKind === "result_unknown") return "远端终态未知";
  if (failureKind === "restart_interrupted") return "重启中断";
  if (failureKind === "timed_out") return "已超时";
  return "执行失败";
}

export function costLabel(
  costMicros: number | null,
  currency: string,
  status: "reported" | "estimated" | "unavailable"
): string {
  if (status === "unavailable" || costMicros === null) return "费用待确认";
  return `${currency} ${(costMicros / 1_000_000).toFixed(6)}`;
}

export function executionError(
  error: unknown,
  fallback: string
): AIConfigUiError {
  const mapped = toAIConfigUiError(error, fallback);
  if (
    error instanceof RuntimeError
    && [
      "AI_DEPENDENCY_INVALID",
      "AI_PROVIDER_REAL_VALIDATION_REQUIRED",
      "AI_KNOWLEDGE_TEXT_CONTEXT_UNAVAILABLE",
      "AI_KNOWLEDGE_SNAPSHOT_NOT_READY"
    ].includes(error.errorCode)
  ) {
    return { ...mapped, retryable: false };
  }
  return mapped;
}

export function shortHash(value: string | null | undefined): string {
  return value ? `${value.slice(0, 8)}…${value.slice(-6)}` : "—";
}
