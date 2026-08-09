import { defineComponent, onMounted } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RuntimeError } from "@/app/runtime-client/core";

const taskApi = vi.hoisted(() => ({
  getAccountTask: vi.fn(),
  listAccountTasks: vi.fn()
}));
const connection = vi.hoisted(() => ({
  recoveryListener: null as null | (() => void | Promise<void>)
}));

vi.mock("@/app/runtime-client/tasks", () => taskApi);
vi.mock("@/app/runtime-client/connection", () => ({
  onDesktopRuntimeConnectionRecovered: vi.fn((listener: () => void | Promise<void>) => {
    connection.recoveryListener = listener;
    return vi.fn();
  })
}));

import { waitForAccountTask } from "@/app/runtime-client/task-polling";
import { useAccountTaskProjection } from "@/modules/tasks/use-account-task-projection";

describe("P0-G 持久任务恢复", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    connection.recoveryListener = null;
  });

  it("Runtime generation 切换时继续轮询同一持久任务", async () => {
    taskApi.getAccountTask
      .mockRejectedValueOnce(new RuntimeError("Runtime 已切换", {
        errorCode: "RUNTIME_CONNECTION_CHANGED",
        status: 503
      }))
      .mockResolvedValueOnce({ data: completedTask("task-recovered") });
    const controller = new AbortController();

    await expect(waitForAccountTask("account-a", "task-recovered", {
      signal: controller.signal,
      timeoutMs: 500,
      pollIntervalMs: 1
    })).resolves.toMatchObject({
      taskId: "task-recovered",
      completionKind: "succeeded"
    });
    expect(taskApi.getAccountTask).toHaveBeenCalledTimes(2);
  });

  it("页面重建和 Runtime 恢复后从服务端任务列表重建投影", async () => {
    taskApi.listAccountTasks
      .mockResolvedValueOnce({ data: { items: [] } })
      .mockResolvedValueOnce({ data: { items: [completedTask("task-after-restart")] } });
    const TestHost = defineComponent({
      setup() {
        const projection = useAccountTaskProjection();
        onMounted(() => projection.load("account-a"));
        return {
          projectionState: projection.state,
          projectedTasks: projection.tasks
        };
      },
      template: `
        <div>
          <span data-testid="state">{{ projectionState }}</span>
          <span data-testid="task">{{ projectedTasks[0]?.taskId ?? "none" }}</span>
        </div>
      `
    });
    const wrapper = mount(TestHost);
    await flushPromises();
    expect(wrapper.get("[data-testid='state']").text()).toBe("empty");

    await connection.recoveryListener?.();
    await flushPromises();

    expect(wrapper.get("[data-testid='state']").text()).toBe("ready");
    expect(wrapper.get("[data-testid='task']").text()).toBe("task-after-restart");
    expect(taskApi.listAccountTasks).toHaveBeenLastCalledWith(
      "account-a",
      50,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    wrapper.unmount();
  });
});

function completedTask(taskId: string) {
  return {
    taskId,
    scope: "account",
    accountId: "account-a",
    taskType: "execution_environment.provision",
    status: "completed",
    cancellable: false,
    createdAt: "2026-08-02T10:00:00Z",
    completionKind: "succeeded",
    failureKind: null,
    progress: 1,
    resultRef: "environment-a",
    errorCode: null,
    logId: null,
    revision: 4
  } as const;
}
