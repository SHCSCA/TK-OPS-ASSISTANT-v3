import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WizardAccountLogin from "@/modules/accounts/components/wizard/WizardAccountLogin.vue";

const loginApi = vi.hoisted(() => ({
  cancelAccountLoginSession: vi.fn(),
  createAccountLoginSession: vi.fn(),
  getAccountLoginSession: vi.fn(),
  probeAccountLoginSession: vi.fn()
}));
const taskPolling = vi.hoisted(() => ({ waitForAccountTask: vi.fn() }));
const taskApi = vi.hoisted(() => ({ cancelAccountTask: vi.fn() }));

vi.mock("@/app/runtime-client/account-login-sessions", () => loginApi);
vi.mock("@/app/runtime-client/task-polling", () => taskPolling);
vi.mock("@/app/runtime-client/tasks", () => taskApi);

describe("P0-G 账号监督登录", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    loginApi.createAccountLoginSession.mockResolvedValue({
      data: { sessionId: "login-1", taskId: "task-prepare", state: "preparing" }
    });
    loginApi.probeAccountLoginSession.mockResolvedValue({
      data: { sessionId: "login-1", taskId: "task-probe", state: "probing" }
    });
    taskPolling.waitForAccountTask.mockResolvedValue({ status: "completed" });
    taskApi.cancelAccountTask.mockResolvedValue({ data: { status: "completed" } });
  });

  it("只引导用户在可见浏览器登录，探测成功后进入下一步", async () => {
    loginApi.getAccountLoginSession
      .mockResolvedValueOnce({ data: sessionFixture({ state: "waiting_user" }) })
      .mockResolvedValueOnce({ data: sessionFixture({ state: "waiting_user" }) })
      .mockResolvedValueOnce({
        data: sessionFixture({
          state: "completed",
          detectedIdentity: "efficiency.lab",
          revision: 4
        })
      });
    const wrapper = mount(WizardAccountLogin, {
      props: { accountId: "account-1", environmentId: "env-1" }
    });

    expect(wrapper.find('input[type="password"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Cookie");
    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("请在浏览器中自行登录");
    expect(wrapper.text()).toContain("我已完成登录");
    await wrapper.findAll("button.account-button.is-primary")[0].trigger("click");
    await flushPromises();

    expect(loginApi.probeAccountLoginSession).toHaveBeenCalledWith(
      "account-1",
      "login-1",
      2,
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(wrapper.emitted("authenticated")).toEqual([["efficiency.lab"]]);
  });

  it("身份不一致时展示目标与检测到的公开 handle，不伪装成功", async () => {
    loginApi.getAccountLoginSession
      .mockResolvedValueOnce({ data: sessionFixture({ state: "waiting_user" }) })
      .mockResolvedValueOnce({ data: sessionFixture({ state: "waiting_user" }) })
      .mockResolvedValueOnce({
        data: sessionFixture({
          state: "waiting_user",
          detectedIdentity: "wrong.account",
          errorCode: "ACCOUNT_PLATFORM_IDENTITY_MISMATCH",
          errorLogId: "log-1",
          revision: 4
        })
      });
    taskPolling.waitForAccountTask
      .mockResolvedValueOnce({ status: "completed" })
      .mockRejectedValueOnce(new Error("身份不一致"));
    const wrapper = mount(WizardAccountLogin, {
      props: { accountId: "account-1", environmentId: "env-1" }
    });

    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();
    await wrapper.findAll("button.account-button.is-primary")[0].trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("目标：@efficiency.lab");
    expect(wrapper.text()).toContain("检测到：@wrong.account");
    expect(wrapper.text()).toContain("查看日志");
    expect(wrapper.emitted("authenticated")).toBeUndefined();
  });

  it("准备阶段取消会携带会话与任务上下文", async () => {
    loginApi.getAccountLoginSession
      .mockResolvedValueOnce({ data: sessionFixture({ state: "preparing" }) })
      .mockResolvedValueOnce({ data: sessionFixture({ state: "cancelled", revision: 3 }) });
    loginApi.cancelAccountLoginSession.mockResolvedValue({
      data: sessionFixture({ state: "cancelled", revision: 3 })
    });
    taskPolling.waitForAccountTask.mockImplementation(
      () => new Promise(() => undefined)
    );
    const wrapper = mount(WizardAccountLogin, {
      props: { accountId: "account-1", environmentId: "env-1" }
    });

    await wrapper.get("button.account-button.is-primary").trigger("click");
    await flushPromises();
    await wrapper.get("button.account-button.is-secondary").trigger("click");
    await flushPromises();

    expect(loginApi.cancelAccountLoginSession).toHaveBeenCalledWith(
      "account-1",
      "login-1",
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(taskApi.cancelAccountTask).toHaveBeenCalledWith(
      "account-1",
      "task-prepare",
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(wrapper.emitted("cancelled")).toEqual([[]]);
    expect(wrapper.text()).toContain("登录已取消");
    expect(wrapper.get("button.account-button.is-primary").text())
      .toContain("重新开始登录");
  });
});

function sessionFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "login-1",
    accountId: "account-1",
    environmentId: "env-1",
    state: "waiting_user",
    expectedIdentity: "efficiency.lab",
    detectedIdentity: null,
    expiresAt: "2026-08-02T01:00:00Z",
    prepareTaskId: "task-prepare",
    probeTaskId: null,
    errorCode: null,
    errorLogId: null,
    revision: 2,
    ...overrides
  };
}
