import { mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProviderWorkspace from "@/modules/system/ai-config/components/ProviderWorkspace.vue";
import { useProviderConfigStore } from "@/modules/system/ai-config/provider-config-store";

import {
  capabilityFixture,
  modelFixture,
  providerFixture,
  result
} from "./ai-system-fixtures";

const aiApi = vi.hoisted(() => ({
  startModelCapabilityCheck: vi.fn(),
  startProviderCheck: vi.fn(),
  startProviderModelDiscovery: vi.fn()
}));

vi.mock("@/app/runtime-client/ai-system", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/app/runtime-client/ai-system")>(),
  startModelCapabilityCheck: aiApi.startModelCapabilityCheck,
  startProviderCheck: aiApi.startProviderCheck,
  startProviderModelDiscovery: aiApi.startProviderModelDiscovery
}));

describe("P0-H Provider 四阶段真实验证", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    aiApi.startModelCapabilityCheck.mockResolvedValue(result(taskAccepted()));
    aiApi.startProviderCheck.mockResolvedValue(result(taskAccepted()));
    aiApi.startProviderModelDiscovery.mockResolvedValue(result(taskAccepted()));
  });

  it("在 Provider 详情明确展示网络、鉴权、模型发现和真实小调用", () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useProviderConfigStore();
    store.providers = [providerFixture()];
    store.models = [modelFixture()];
    store.capabilities = [capabilityFixture()];
    store.state = "ready";
    store.selectProvider("provider-1");

    const wrapper = mount(ProviderWorkspace, {
      global: { plugins: [pinia] }
    });
    const panel = wrapper.get('[data-testid="provider-real-validation"]');

    expect(panel.text()).toContain("四阶段真实验证");
    expect(panel.text()).toContain("网络");
    expect(panel.text()).toContain("鉴权");
    expect(panel.text()).toContain("模型发现");
    expect(panel.text()).toContain("真实小调用");
    expect(panel.findAll("li.is-verified")).toHaveLength(4);
    expect(button(wrapper, "验证网络与鉴权").exists()).toBe(true);
    expect(button(wrapper, "验证模型发现").exists()).toBe(true);
    expect(button(wrapper, "验证真实小调用").exists()).toBe(true);
  });

  it("真实小调用固定走 Runtime real_small_call 模式并要求 usage 证据", async () => {
    const store = useProviderConfigStore();
    const provider = providerFixture();
    store.providers = [provider];
    store.models = [modelFixture()];
    store.selectProvider(provider.id);

    expect(await store.runRealSmallCall(provider)).toBe(true);
    expect(aiApi.startModelCapabilityCheck).toHaveBeenCalledWith(
      "model-1",
      {
        capabilityKeys: ["script_generation"],
        force: true,
        mode: "real_small_call"
      },
      expect.objectContaining({ idempotencyKey: expect.any(String) })
    );
    expect(store.validationOperation).toBe("real_small_call");
    expect(store.feedback).toContain("usage");
  });

  it("没有模型时失败封闭并给出可执行提示", async () => {
    const store = useProviderConfigStore();
    const provider = providerFixture();
    store.providers = [provider];
    store.selectProvider(provider.id);
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(await store.runRealSmallCall(provider)).toBe(false);
    expect(store.error?.message).toContain("先发现或手动添加模型");
    expect(aiApi.startModelCapabilityCheck).not.toHaveBeenCalled();
  });
});

function button(wrapper: VueWrapper, label: string) {
  const candidate = wrapper.findAll("button").find(
    (item) => item.text().trim() === label
  );
  if (!candidate) throw new Error(`未找到按钮：${label}`);
  return candidate;
}

function taskAccepted() {
  return {
    taskId: "task-provider-validation",
    scope: "system" as const,
    accountId: null,
    taskType: "model.capability_check",
    status: "queued" as const,
    cancellable: true,
    createdAt: "2026-08-10T10:00:00Z"
  };
}
