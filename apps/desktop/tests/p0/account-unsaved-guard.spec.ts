import { describe, expect, it, vi } from "vitest";

import {
  AccountUnsavedDecisionController,
  UnsavedGuardRegistry
} from "@/app/account-context";

describe("P0 账号未保存守卫", () => {
  it("把脏数据来源交给统一决策端口，保存完成后才允许继续", async () => {
    let dirty = true;
    const save = vi.fn(async () => {
      dirty = false;
    });
    const discard = vi.fn(() => {
      dirty = false;
    });
    const decisions = new AccountUnsavedDecisionController();
    const registry = new UnsavedGuardRegistry(decisions, logger());
    registry.register({
      id: "topic-draft",
      label: "选题草稿",
      isDirty: () => dirty,
      save,
      discard
    });

    const operation = registry.run({
      reason: "account-switch",
      sourceAccountId: "account-source",
      targetAccountId: "account-target",
      signal: new AbortController().signal
    });

    expect(decisions.state.pending?.prompt.guards).toEqual([
      { id: "topic-draft", label: "选题草稿" }
    ]);
    decisions.resolve("save");

    await expect(operation).resolves.toEqual({
      status: "saved",
      guardIds: ["topic-draft"]
    });
    expect(save).toHaveBeenCalledOnce();
    expect(discard).not.toHaveBeenCalled();
  });

  it("取消决策时不保存、不丢弃并保持脏状态", async () => {
    const save = vi.fn();
    const discard = vi.fn();
    const decisions = new AccountUnsavedDecisionController();
    const registry = new UnsavedGuardRegistry(decisions, logger());
    registry.register({
      id: "storyboard-draft",
      label: "分镜草稿",
      isDirty: () => true,
      save,
      discard
    });

    const operation = registry.run({
      reason: "route-leave",
      sourceAccountId: "account-current",
      targetAccountId: null,
      signal: new AbortController().signal
    });
    decisions.resolve("cancel");

    await expect(operation).resolves.toEqual({
      status: "cancelled",
      guardIds: ["storyboard-draft"]
    });
    expect(save).not.toHaveBeenCalled();
    expect(discard).not.toHaveBeenCalled();
  });

  it("切换意图被中止时关闭待决窗口并返回取消", async () => {
    const decisions = new AccountUnsavedDecisionController();
    const controller = new AbortController();
    const prompt = {
      reason: "account-switch" as const,
      sourceAccountId: "account-source",
      targetAccountId: "account-target",
      guards: [{ id: "script-draft", label: "脚本草稿" }],
      signal: controller.signal
    };

    const operation = decisions.decide(prompt);
    expect(decisions.state.pending?.prompt).toBe(prompt);

    controller.abort();

    await expect(operation).resolves.toBe("cancel");
    expect(decisions.state.pending).toBeNull();
  });
});

function logger() {
  return {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  };
}
