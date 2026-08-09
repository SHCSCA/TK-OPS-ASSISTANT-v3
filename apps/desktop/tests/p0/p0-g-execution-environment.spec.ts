import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExecutionEnvironmentCreator from "@/modules/execution-environments/components/ExecutionEnvironmentCreator.vue";
import type { ExecutionEnvironmentDto } from "@/types/runtime/execution-environments";

const workspaceBridge = vi.hoisted(() => ({
  pickAccountWorkspaceRoot: vi.fn()
}));
const environmentApi = vi.hoisted(() => ({
  createExecutionEnvironment: vi.fn(),
  getExecutionEnvironment: vi.fn(),
  retryExecutionEnvironment: vi.fn()
}));
const taskApi = vi.hoisted(() => ({
  cancelAccountTask: vi.fn(),
  getAccountTask: vi.fn()
}));

vi.mock("@/app/workspace-roots", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/app/workspace-roots")>();
  return { ...original, ...workspaceBridge };
});
vi.mock("@/app/runtime-client/execution-environments", () => environmentApi);
vi.mock("@/app/runtime-client/tasks", () => taskApi);

describe("P0-G 执行环境创建交互", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspaceBridge.pickAccountWorkspaceRoot.mockResolvedValue({
      displayName: "效率观察",
      displayPath: "D:\\TK-OPS\\效率观察",
      revision: 1,
      rootRef: "wr_0123456789abcdef0123456789abcdef",
      status: "active"
    });
    environmentApi.createExecutionEnvironment.mockResolvedValue({
      data: { environmentId: "env-1", taskId: "task-1" },
      meta: null,
      operationId: null,
      requestId: "request-1",
      status: 202
    });
    environmentApi.getExecutionEnvironment.mockResolvedValue({
      data: failedEnvironmentFixture()
    });
    taskApi.getAccountTask.mockResolvedValue({
      data: {
        taskId: "task-1",
        scope: "account",
        accountId: "account-1",
        taskType: "execution_environment.provision",
        status: "completed",
        cancellable: false,
        createdAt: "2026-08-02T00:00:00Z",
        completionKind: "succeeded",
        failureKind: null,
        progress: 1,
        resultRef: "env-1",
        errorCode: null,
        logId: null,
        revision: 2
      },
      meta: null,
      operationId: null,
      requestId: "request-2",
      status: 200
    });
  });

  it("显示用户选择的工作目录，但只把 rootRef 发送给 Runtime", async () => {
    const wrapper = mount(ExecutionEnvironmentCreator, {
      props: { accountId: "account-1", accountName: "效率观察" }
    });

    await wrapper.get("button.account-button.is-secondary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("D:\\TK-OPS\\效率观察");
    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();

    expect(environmentApi.createExecutionEnvironment).toHaveBeenCalledWith(
      "account-1",
      expect.objectContaining({
        name: "主执行环境",
        rootRef: "wr_0123456789abcdef0123456789abcdef"
      }),
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    const serializedCall = JSON.stringify(
      environmentApi.createExecutionEnvironment.mock.calls[0]
    );
    expect(serializedCall).not.toContain("D:\\\\TK-OPS");
    expect(wrapper.emitted("created")).toEqual([["env-1"]]);
  });

  it("任务失败时展示错误和日志入口，不伪装为可绑定", async () => {
    taskApi.getAccountTask.mockResolvedValueOnce({
      data: {
        status: "failed",
        completionKind: null,
        errorCode: "BROWSER_PROCESS_OWNERSHIP_UNPROVEN",
        logId: "log-1"
      }
    });
    const wrapper = mount(ExecutionEnvironmentCreator, {
      props: { accountId: "account-1", accountName: "效率观察" }
    });

    await wrapper.get("button.account-button.is-secondary").trigger("click");
    await flushPromises();
    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("执行环境创建失败");
    expect(wrapper.text()).toContain("查看日志");
    expect(wrapper.emitted("created")).toBeUndefined();
  });

  it("失败后沿用原环境与原任务重试，不重新选择目录", async () => {
    environmentApi.retryExecutionEnvironment.mockResolvedValue({
      data: {
        environmentId: "env-1",
        taskId: "task-retry",
        retryOfTaskId: "task-1"
      }
    });
    const wrapper = mount(ExecutionEnvironmentCreator, {
      props: {
        accountId: "account-1",
        accountName: "效率观察",
        existingEnvironment: failedEnvironmentFixture()
      }
    });

    expect(wrapper.text()).toContain("恢复执行环境");
    expect(wrapper.text()).toContain("D:\\TK-OPS\\效率观察");
    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();

    expect(environmentApi.retryExecutionEnvironment).toHaveBeenCalledWith(
      "account-1",
      "env-1",
      3,
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(environmentApi.createExecutionEnvironment).not.toHaveBeenCalled();
    expect(wrapper.emitted("created")).toEqual([["env-1"]]);
  });
});

function failedEnvironmentFixture(): ExecutionEnvironmentDto {
  return {
    id: "env-1",
    accountId: "account-1",
    name: "主执行环境",
    status: "failed",
    workspace: {
      id: "workspace-1",
      rootRef: "wr_0123456789abcdef0123456789abcdef",
      displayName: "D:\\TK-OPS\\效率观察",
      status: "failed",
      ownershipState: "owned"
    },
    browser: {
      id: "browser-1",
      kind: "chrome",
      displayName: "Google Chrome",
      status: "failed",
      ownershipVerified: false,
      lastCheckedAt: null
    },
    eligibility: {
      eligible: false,
      blockingIssues: [],
      checkedAt: "2026-08-09T00:00:00Z",
      evidenceRevision: 3
    },
    revision: 3,
    errorCode: "EXECUTION_ENVIRONMENT_PROVISION_FAILED",
    errorLogId: "log-1",
    errorMessage: "执行环境创建失败，请查看日志后重试。",
    lastTaskId: "task-1",
    lastRetryOfTaskId: null,
    recoveryActions: ["retry_provision", "check", "view_log"]
  };
}
