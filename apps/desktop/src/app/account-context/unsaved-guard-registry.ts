import { AccountSwitchSupersededError } from "./errors";
import type {
  AccountContextLoggerPort,
  UnsavedGuard,
  UnsavedGuardDecisionPort,
  UnsavedGuardPrompt,
  UnsavedGuardRunResult
} from "./types";

type GuardExecutionPhase = "inspect" | "prompt" | "save" | "discard";

export class UnsavedGuardExecutionError extends Error {
  readonly code = "UNSAVED_GUARD_FAILED";

  constructor(
    readonly guardId: string | null,
    readonly phase: GuardExecutionPhase,
    cause: unknown
  ) {
    const label = guardId ? `“${guardId}”` : "未保存内容";
    super(`${label}在${phaseLabel(phase)}时失败。`, { cause });
    this.name = "UnsavedGuardExecutionError";
  }
}

export class UnsavedGuardRegistry {
  private readonly guards = new Map<string, UnsavedGuard>();

  constructor(
    private readonly decisions: UnsavedGuardDecisionPort,
    private readonly logger: AccountContextLoggerPort = consoleAccountContextLogger
  ) {}

  register(guard: UnsavedGuard): () => void {
    const id = guard.id.trim();
    const label = guard.label.trim();
    if (!id || !label) {
      throw new Error("未保存守卫必须提供非空 id 和 label。");
    }
    if (this.guards.has(id)) {
      throw new Error(`未保存守卫 ${id} 已注册。`);
    }

    const registered = { ...guard, id, label };
    this.guards.set(id, registered);
    return () => {
      if (this.guards.get(id) === registered) {
        this.guards.delete(id);
      }
    };
  }

  unregister(id: string): void {
    this.guards.delete(id);
  }

  clear(): void {
    this.guards.clear();
  }

  inspectDirty(): UnsavedGuard[] {
    const dirty: UnsavedGuard[] = [];
    for (const guard of this.guards.values()) {
      try {
        if (guard.isDirty()) dirty.push(guard);
      } catch (error) {
        this.logger.error("[account-context] 检查未保存状态失败", {
          guardId: guard.id,
          error
        });
        throw new UnsavedGuardExecutionError(guard.id, "inspect", error);
      }
    }
    return dirty;
  }

  async run(
    prompt: Omit<UnsavedGuardPrompt, "guards">
  ): Promise<UnsavedGuardRunResult> {
    assertNotAborted(prompt.signal);
    const dirty = this.inspectDirty();
    if (dirty.length === 0) return { status: "clean" };

    let decision;
    try {
      decision = await this.decisions.decide({
        ...prompt,
        guards: dirty.map(({ id, label }) => ({ id, label }))
      });
    } catch (error) {
      if (prompt.signal.aborted) throw new AccountSwitchSupersededError();
      this.logger.error("[account-context] 未保存确认交互失败", error);
      throw new UnsavedGuardExecutionError(null, "prompt", error);
    }

    assertNotAborted(prompt.signal);
    if (decision !== "save" && decision !== "discard" && decision !== "cancel") {
      const error = new Error("未保存确认返回了不受支持的决策。");
      this.logger.error("[account-context] 未保存确认决策无效", decision);
      throw new UnsavedGuardExecutionError(null, "prompt", error);
    }
    const guardIds = dirty.map((guard) => guard.id);
    if (decision === "cancel") {
      return { status: "cancelled", guardIds };
    }

    const phase = decision === "save" ? "save" : "discard";
    for (const guard of dirty) {
      assertNotAborted(prompt.signal);
      try {
        if (decision === "save") {
          await guard.save();
        } else {
          await guard.discard();
        }
        if (guard.isDirty()) {
          throw new Error(
            decision === "save"
              ? "保存完成后仍存在未保存内容。"
              : "放弃完成后仍存在未保存内容。"
          );
        }
      } catch (error) {
        if (prompt.signal.aborted) throw new AccountSwitchSupersededError();
        this.logger.error("[account-context] 处理未保存内容失败", {
          guardId: guard.id,
          phase,
          error
        });
        throw new UnsavedGuardExecutionError(guard.id, phase, error);
      }
    }

    return decision === "save"
      ? { status: "saved", guardIds }
      : { status: "discarded", guardIds };
  }
}

export const consoleAccountContextLogger: AccountContextLoggerPort = {
  debug: (message, details) => console.debug(message, details ?? ""),
  info: (message, details) => console.info(message, details ?? ""),
  warn: (message, details) => console.warn(message, details ?? ""),
  error: (message, details) => console.error(message, details ?? "")
};

function assertNotAborted(signal: AbortSignal): void {
  if (signal.aborted) throw new AccountSwitchSupersededError();
}

function phaseLabel(phase: GuardExecutionPhase): string {
  const labels: Record<GuardExecutionPhase, string> = {
    inspect: "检查未保存状态",
    prompt: "打开确认窗口",
    save: "保存内容",
    discard: "放弃内容"
  };
  return labels[phase];
}
