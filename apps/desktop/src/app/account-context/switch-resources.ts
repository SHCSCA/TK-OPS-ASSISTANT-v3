import type {
  AccountContextLoggerPort,
  ReversibleAccountSwitchResource
} from "./types";

type ResourceEntry = {
  label: string;
  resource: ReversibleAccountSwitchResource;
  committed: boolean;
};

export class PreparedAccountResourceStack {
  private readonly entries: ResourceEntry[] = [];
  private rollbackOperation: Promise<void> | null = null;
  private finalizeOperation: Promise<void> | null = null;

  constructor(private readonly logger: AccountContextLoggerPort) {}

  add(label: string, resource: ReversibleAccountSwitchResource): void {
    if (this.rollbackOperation || this.finalizeOperation) {
      throw new Error("账号切换资源栈已经开始收口，不能继续添加资源。");
    }
    this.entries.push({ label, resource, committed: false });
  }

  async commitAll(assertCurrent: () => void): Promise<void> {
    for (const entry of this.entries) {
      assertCurrent();
      await entry.resource.commit();
      entry.committed = true;
    }
  }

  rollback(reason?: unknown): Promise<void> {
    if (this.finalizeOperation) return this.finalizeOperation;
    if (this.rollbackOperation) return this.rollbackOperation;
    this.rollbackOperation = this.runRollback(reason);
    return this.rollbackOperation;
  }

  finalize(): Promise<void> {
    if (this.rollbackOperation) return this.rollbackOperation;
    if (this.finalizeOperation) return this.finalizeOperation;
    this.finalizeOperation = this.runFinalize();
    return this.finalizeOperation;
  }

  private async runRollback(reason?: unknown): Promise<void> {
    const failures: Array<{ label: string; error: unknown }> = [];
    for (const entry of [...this.entries].reverse()) {
      try {
        await entry.resource.rollback(reason);
      } catch (error) {
        failures.push({ label: entry.label, error });
        this.logger.error("[account-context] 回滚账号切换资源失败", {
          resource: entry.label,
          committed: entry.committed,
          error
        });
      }
    }
    if (failures.length > 0) {
      throw new AggregateError(
        failures.map((item) => item.error),
        "账号切换资源回滚不完整。"
      );
    }
  }

  private async runFinalize(): Promise<void> {
    for (const entry of this.entries) {
      if (!entry.resource.finalize) continue;
      try {
        await entry.resource.finalize();
      } catch (error) {
        this.logger.error("[account-context] 收口账号切换资源失败", {
          resource: entry.label,
          error
        });
      }
    }
  }
}
