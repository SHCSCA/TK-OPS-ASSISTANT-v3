import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RuntimeError } from "@/app/runtime-client/core";

import {
  capabilityFixture,
  modelFixture,
  promptProfileFixture,
  providerFixture,
  result,
  routeFixture
} from "./ai-system-fixtures";

const aiApi = vi.hoisted(() => ({
  createModelProfile: vi.fn(),
  listCapabilityRoutes: vi.fn(),
  listModelCapabilities: vi.fn(),
  listModelProfiles: vi.fn(),
  listPromptProfiles: vi.fn(),
  listProviderProfiles: vi.fn(),
  patchProviderProfile: vi.fn(),
  startModelCapabilityCheck: vi.fn(),
  startProviderCheck: vi.fn(),
  startProviderModelDiscovery: vi.fn(),
  updateCapabilityRoute: vi.fn(),
  validateCapabilityRoute: vi.fn()
}));
const taskApi = vi.hoisted(() => ({
  cancelSystemTask: vi.fn(),
  getSystemTask: vi.fn()
}));

vi.mock("@/app/runtime-client/ai-system", () => aiApi);
vi.mock("@/app/runtime-client/tasks", () => taskApi);

import { useModelRouteConfigStore } from "@/modules/system/ai-config/model-route-config-store";
import { useProviderConfigStore } from "@/modules/system/ai-config/provider-config-store";

describe("P0-E Provider、模型与 Route store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockEmptyLists();
  });

  it("Provider 从 loading 进入首次使用空态", async () => {
    const pending = deferred<ReturnType<typeof result>>();
    aiApi.listProviderProfiles.mockReturnValueOnce(pending.promise);
    const store = useProviderConfigStore();

    const loading = store.load();
    expect(store.state).toBe("loading");
    pending.resolve(result({ items: [], totalKnown: 0 }));
    await loading;

    expect(store.state).toBe("first_use");
    expect(store.providers).toEqual([]);
    expect(store.totalKnown).toBe(0);
  });

  it("Provider 正常态、过滤空态与清除筛选保持同一真实集合", async () => {
    aiApi.listProviderProfiles.mockResolvedValueOnce(result({
      items: [providerFixture()],
      totalKnown: 1
    }));
    aiApi.listModelProfiles.mockResolvedValueOnce(result({
      items: [modelFixture()],
      totalKnown: 1
    }));
    const store = useProviderConfigStore();

    await store.load();
    expect(store.state).toBe("ready");
    expect(store.modelsForProvider("provider-1")).toHaveLength(1);

    store.search = "不存在";
    store.recomputeState();
    expect(store.state).toBe("filtered_empty");

    store.clearFilters();
    expect(store.state).toBe("ready");
    expect(store.filteredProviders[0]?.name).toBe("本机 OpenAI 兼容服务");
  });

  it("Provider 错误态保留 Runtime 日志并可通过重新加载恢复", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    aiApi.listProviderProfiles.mockRejectedValueOnce(
      new RuntimeError("Provider 服务不可用。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-provider",
        status: 503
      })
    );
    const store = useProviderConfigStore();

    await store.load();
    expect(store.state).toBe("error");
    expect(store.error).toMatchObject({
      message: "Provider 服务不可用。",
      logId: "log-provider",
      retryable: true
    });

    aiApi.listProviderProfiles.mockResolvedValueOnce(result({
      items: [providerFixture()],
      totalKnown: 1
    }));
    await store.load();
    expect(store.state).toBe("ready");
    expect(store.error).toBeNull();
  });

  it("Provider 保存使用现有修订并在成功后刷新配置", async () => {
    const store = useProviderConfigStore();
    const provider = providerFixture({ revision: 7 });
    store.providers = [provider];
    store.state = "ready";
    aiApi.patchProviderProfile.mockResolvedValueOnce(
      result(providerFixture({ enabled: false, revision: 8 }))
    );
    aiApi.listProviderProfiles.mockResolvedValueOnce(result({
      items: [providerFixture({ enabled: false, revision: 8 })],
      totalKnown: 1
    }));

    expect(await store.updateProvider(provider, { enabled: false })).toBe(true);
    expect(aiApi.patchProviderProfile).toHaveBeenCalledWith(
      "provider-1",
      { enabled: false },
      { expectedRevision: 7 }
    );
    expect(store.feedback).toContain("重新校验");
  });

  it("模型工作面区分系统首次使用、模型依赖阻塞和正常能力矩阵", async () => {
    const store = useModelRouteConfigStore();

    await store.load();
    expect(store.state).toBe("first_use");

    aiApi.listProviderProfiles.mockResolvedValueOnce(result({
      items: [providerFixture()],
      totalKnown: 1
    }));
    await store.load();
    expect(store.state).toBe("dependency_blocked");

    mockModelRouteLists();
    await store.load();
    expect(store.state).toBe("ready");
    expect(store.eligibleModels("script_generation")).toEqual([
      expect.objectContaining({ id: "model-1" })
    ]);
    expect(store.promptsFor("script_generation")).toEqual([
      expect.objectContaining({
        profileKey: "script-default",
        activeVersionId: "prompt-version-1"
      })
    ]);
  });

  it("手动模型创建只登记真实模型并提示继续能力契约验证", async () => {
    const store = useModelRouteConfigStore();
    const input = {
      providerProfileId: "provider-1",
      modelId: "qwen-plus",
      displayName: "Qwen Plus",
      enabled: true
    };
    aiApi.createModelProfile.mockResolvedValueOnce(result(modelFixture(), 201));
    mockModelRouteLists();

    expect(await store.createManualModel(input)).toBe(true);
    expect(aiApi.createModelProfile).toHaveBeenCalledWith(
      input,
      expect.objectContaining({
        idempotencyKey: expect.stringContaining("model-create:provider-1:")
      })
    );
    expect(store.selectedModelId).toBe("model-1");
    expect(store.feedback).toContain("继续运行能力契约验证");
  });

  it("fresh DB 首 Route 以修订 0 创建并传递 Prompt 激活版本行 ID", async () => {
    const store = useModelRouteConfigStore();
    const input = {
      primaryModelProfileId: "model-1",
      fallbackModelProfileId: null,
      promptProfileId: "prompt-version-1",
      enabled: true
    };
    aiApi.updateCapabilityRoute.mockResolvedValueOnce(result(routeFixture()));
    mockModelRouteLists();

    expect(await store.createRoute("script_generation", input)).toBe(true);
    expect(aiApi.updateCapabilityRoute).toHaveBeenCalledWith(
      "script_generation",
      input,
      expect.objectContaining({
        expectedRevision: 0,
        idempotencyKey: expect.stringContaining(
          "route-create:script_generation:"
        )
      })
    );
    expect(store.mode).toBe("routes");
    expect(store.selectedCapabilityKey).toBe("script_generation");
  });

  it("既有 Route 原子保存使用自身修订并提交能力验证", async () => {
    const store = useModelRouteConfigStore();
    const route = routeFixture({ revision: 6 });
    const input = {
      primaryModelProfileId: "model-1",
      fallbackModelProfileId: "model-2",
      promptProfileId: "prompt-version-1",
      enabled: true
    };
    aiApi.updateCapabilityRoute.mockResolvedValueOnce(result({
      ...route,
      ...input,
      revision: 7
    }));
    aiApi.validateCapabilityRoute.mockResolvedValueOnce(result(route));
    mockModelRouteLists();
    mockModelRouteLists();

    expect(await store.saveRoute(route, input)).toBe(true);
    expect(aiApi.updateCapabilityRoute).toHaveBeenCalledWith(
      "script_generation",
      input,
      expect.objectContaining({ expectedRevision: 6 })
    );
    expect(await store.validateRoute(route)).toBe(true);
    expect(aiApi.validateCapabilityRoute).toHaveBeenCalledWith(
      "script_generation",
      expect.objectContaining({
        idempotencyKey: expect.stringContaining(
          "route-validate:script_generation:"
        )
      })
    );
  });
});

function mockEmptyLists(): void {
  aiApi.listProviderProfiles.mockResolvedValue(
    result({ items: [], totalKnown: 0 })
  );
  aiApi.listModelProfiles.mockResolvedValue(
    result({ items: [], totalKnown: 0 })
  );
  aiApi.listModelCapabilities.mockResolvedValue(
    result({ items: [], totalKnown: 0 })
  );
  aiApi.listCapabilityRoutes.mockResolvedValue(
    result({ items: [], totalKnown: 0 })
  );
  aiApi.listPromptProfiles.mockResolvedValue(
    result({ items: [], totalKnown: 0 })
  );
}

function mockModelRouteLists(): void {
  aiApi.listProviderProfiles.mockResolvedValueOnce(result({
    items: [providerFixture()],
    totalKnown: 1
  }));
  aiApi.listModelProfiles.mockResolvedValueOnce(result({
    items: [modelFixture()],
    totalKnown: 1
  }));
  aiApi.listModelCapabilities.mockResolvedValueOnce(result({
    items: [capabilityFixture()],
    totalKnown: 1
  }));
  aiApi.listCapabilityRoutes.mockResolvedValueOnce(result({
    items: [routeFixture()],
    totalKnown: 1
  }));
  aiApi.listPromptProfiles.mockResolvedValueOnce(result({
    items: [promptProfileFixture()],
    totalKnown: 1
  }));
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}
