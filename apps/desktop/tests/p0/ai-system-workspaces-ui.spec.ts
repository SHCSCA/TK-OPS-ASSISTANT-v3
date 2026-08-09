import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CapabilityRouteCreateDialog from "@/modules/system/ai-config/components/CapabilityRouteCreateDialog.vue";
import CapabilityRouteEditor from "@/modules/system/ai-config/components/CapabilityRouteEditor.vue";
import CompositionTemplatePanel from "@/modules/system/ai-config/components/CompositionTemplatePanel.vue";
import ManualModelDialog from "@/modules/system/ai-config/components/ManualModelDialog.vue";
import ModelRouteWorkspace from "@/modules/system/ai-config/components/ModelRouteWorkspace.vue";
import PromptProfilePanel from "@/modules/system/ai-config/components/PromptProfilePanel.vue";
import ProviderWorkspace from "@/modules/system/ai-config/components/ProviderWorkspace.vue";
import { useCompositionTemplateStore } from "@/modules/system/ai-config/composition-template-store";
import { useModelRouteConfigStore } from "@/modules/system/ai-config/model-route-config-store";
import { usePromptConfigStore } from "@/modules/system/ai-config/prompt-config-store";
import { useProviderConfigStore } from "@/modules/system/ai-config/provider-config-store";

import {
  capabilityFixture,
  compositionTemplateFixture,
  modelFixture,
  promptProfileFixture,
  providerFixture,
  routeFixture
} from "./ai-system-fixtures";

describe("P0-E AI 系统工作面 UI", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it("Provider 工作面覆盖加载、首次使用、正常、错误与重试", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useProviderConfigStore();
    store.state = "loading";
    const wrapper = mount(ProviderWorkspace, {
      global: { plugins: [pinia] }
    });

    expect(wrapper.get(".ai-state-panel").attributes("aria-busy")).toBe("true");

    store.state = "first_use";
    await nextTick();
    expect(wrapper.text()).toContain("从第一项真实配置开始");
    expect(wrapper.text()).toContain("添加 Provider");

    store.providers = [providerFixture()];
    store.models = [modelFixture()];
    store.state = "ready";
    await nextTick();
    expect(wrapper.text()).toContain("本机 OpenAI 兼容服务");
    expect(wrapper.text()).toContain("OpenAI-compatible");
    expect(wrapper.text()).toContain("就绪");

    store.providers = [];
    store.models = [];
    store.error = uiError("Provider 读取失败。", "log-provider");
    store.state = "error";
    const retry = vi.spyOn(store, "load").mockResolvedValue(undefined);
    await nextTick();
    expect(wrapper.text()).toContain("Provider 读取失败");
    expect(wrapper.text()).toContain("log-provider");
    await button(wrapper, "重试").trigger("click");
    expect(retry).toHaveBeenCalledOnce();
  });

  it("模型与能力工作面展示空依赖、正常矩阵和能力验证入口", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useModelRouteConfigStore();
    store.providers = [providerFixture()];
    store.state = "dependency_blocked";
    const wrapper = mount(ModelRouteWorkspace, {
      global: { plugins: [pinia] }
    });

    expect(wrapper.text()).toContain("前置依赖尚未就绪");
    expect(wrapper.text()).toContain("手动添加模型");

    store.models = [modelFixture()];
    store.capabilities = [capabilityFixture()];
    store.prompts = [promptProfileFixture()];
    store.state = "ready";
    await nextTick();

    expect(wrapper.text()).toContain("qwen-plus");
    await button(wrapper, "查看矩阵").trigger("click");
    expect(wrapper.text()).toContain("能力契约");
    expect(wrapper.text()).toContain("脚本生成");
    expect(wrapper.text()).toContain("可用");
  });

  it("Route 工作面覆盖空态、新建入口和正常原子编辑", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useModelRouteConfigStore();
    store.providers = [providerFixture()];
    store.models = [modelFixture()];
    store.capabilities = [capabilityFixture()];
    store.prompts = [promptProfileFixture()];
    store.mode = "routes";
    store.state = "empty";
    const wrapper = mount(ModelRouteWorkspace, {
      global: { plugins: [pinia] }
    });

    expect(wrapper.text()).toContain("暂无配置对象");
    await button(wrapper, "新建 Route").trigger("click");
    expect(wrapper.text()).toContain("首条写入使用修订 0");

    store.routes = [routeFixture()];
    store.state = "ready";
    await nextTick();
    expect(wrapper.text()).toContain("默认脚本 Prompt");
    await button(wrapper, "修复").trigger("click");
    expect(wrapper.text()).toContain("原子 Route");
    expect(wrapper.text()).toContain("原子保存 Route");
  });

  it("Prompt 工作面覆盖加载、空态、正常、错误日志与重试", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = usePromptConfigStore();
    store.state = "loading";
    const wrapper = mount(PromptProfilePanel, {
      global: { plugins: [pinia] }
    });
    expect(wrapper.get(".ai-state-panel").attributes("aria-busy")).toBe("true");

    store.state = "first_use";
    await nextTick();
    expect(wrapper.text()).toContain("新建 Prompt");

    store.profiles = [promptProfileFixture()];
    store.state = "ready";
    store.selectProfile("script-default");
    await nextTick();
    expect(wrapper.text()).toContain("默认脚本 Prompt");
    expect(wrapper.text()).toContain("正文按需加载");

    store.closeEditor();
    store.profiles = [];
    store.error = uiError("Prompt 读取失败。", "log-prompt");
    store.state = "error";
    const retry = vi.spyOn(store, "load").mockResolvedValue(undefined);
    await nextTick();
    expect(wrapper.text()).toContain("log-prompt");
    await button(wrapper, "重试").trigger("click");
    expect(retry).toHaveBeenCalledOnce();
  });

  it("合成模板工作面覆盖加载、空态、正常、错误日志与重试", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useCompositionTemplateStore();
    store.state = "loading";
    const wrapper = mount(CompositionTemplatePanel, {
      global: { plugins: [pinia] }
    });
    expect(wrapper.get(".ai-state-panel").attributes("aria-busy")).toBe("true");

    store.state = "first_use";
    await nextTick();
    expect(wrapper.text()).toContain("新建合成模板");

    store.templates = [compositionTemplateFixture()];
    store.state = "ready";
    store.selectTemplate("mixed-default");
    await nextTick();
    expect(wrapper.text()).toContain("默认混合媒体模板");
    expect(wrapper.text()).toContain("模板正文按需加载");

    store.closeEditor();
    store.templates = [];
    store.error = uiError("模板读取失败。", "log-template");
    store.state = "error";
    const retry = vi.spyOn(store, "load").mockResolvedValue(undefined);
    await nextTick();
    expect(wrapper.text()).toContain("log-template");
    await button(wrapper, "重试").trigger("click");
    expect(retry).toHaveBeenCalledOnce();
  });

  it("手动模型和首 Route 表单提交稳定 ID，编辑器使用激活版本行 ID", async () => {
    const manual = mount(ManualModelDialog, {
      props: {
        open: false,
        providers: [providerFixture()]
      }
    });
    await manual.setProps({ open: true });
    const manualInputs = manual.findAll("input");
    await manualInputs[0]?.setValue("qwen-plus");
    await manualInputs[1]?.setValue("Qwen Plus");
    await manual.get("form").trigger("submit");
    expect(manual.emitted("submit")?.[0]).toEqual([{
      providerProfileId: "provider-1",
      modelId: "qwen-plus",
      displayName: "Qwen Plus",
      enabled: true
    }]);

    const createRoute = mount(CapabilityRouteCreateDialog, {
      props: {
        open: false,
        options: [{
          capabilityKey: "script_generation",
          label: "脚本生成",
          models: [modelFixture()],
          prompts: [promptProfileFixture()]
        }]
      }
    });
    await createRoute.setProps({ open: true });
    const selects = createRoute.findAll("select");
    await selects[1]?.setValue("model-1");
    await selects[3]?.setValue("prompt-version-1");
    await createRoute.get("form").trigger("submit");
    expect(createRoute.emitted("submit")?.[0]).toEqual([
      "script_generation",
      {
        primaryModelProfileId: "model-1",
        fallbackModelProfileId: null,
        promptProfileId: "prompt-version-1",
        enabled: false
      }
    ]);

    const editor = mount(CapabilityRouteEditor, {
      props: {
        busy: false,
        eligibleModels: [modelFixture()],
        prompts: [promptProfileFixture()],
        route: routeFixture({ promptProfileId: null })
      }
    });
    await editor.findAll("select")[2]?.setValue("prompt-version-1");
    await button(editor, "原子保存 Route").trigger("click");
    expect(editor.emitted("save")?.[0]?.[0]).toMatchObject({
      promptProfileId: "prompt-version-1"
    });
    await flushPromises();
  });
});

function button(
  wrapper: VueWrapper,
  label: string
) {
  const match = wrapper.findAll("button").find(
    (candidate) => candidate.text().trim() === label
  );
  if (!match) throw new Error(`未找到按钮：${label}`);
  return match;
}

function uiError(message: string, logId: string) {
  return {
    message,
    errorCode: "RUNTIME_NOT_READY",
    logId,
    requestId: "request-p0-e",
    retryable: true
  };
}
