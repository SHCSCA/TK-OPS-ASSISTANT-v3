import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RuntimeError } from "@/app/runtime-client/core";

import {
  compositionTemplateFixture,
  compositionVersionFixture,
  promptProfileFixture,
  promptVersionFixture,
  result
} from "./ai-system-fixtures";

const aiApi = vi.hoisted(() => ({
  activateCompositionTemplateVersion: vi.fn(),
  activatePromptVersion: vi.fn(),
  createCompositionTemplate: vi.fn(),
  createCompositionTemplateVersion: vi.fn(),
  createPromptProfile: vi.fn(),
  createPromptVersion: vi.fn(),
  getCompositionTemplateVersion: vi.fn(),
  getPromptVersion: vi.fn(),
  listCompositionTemplates: vi.fn(),
  listPromptProfiles: vi.fn(),
  validateCompositionTemplateVersion: vi.fn()
}));

vi.mock("@/app/runtime-client/ai-system", () => aiApi);

import { useCompositionTemplateStore } from "@/modules/system/ai-config/composition-template-store";
import { usePromptConfigStore } from "@/modules/system/ai-config/prompt-config-store";

describe("P0-E Prompt 与合成模板 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    aiApi.listPromptProfiles.mockResolvedValue(
      result({ items: [], totalKnown: 0 })
    );
    aiApi.listCompositionTemplates.mockResolvedValue(
      result({ items: [], totalKnown: 0 })
    );
  });

  it("Prompt 覆盖首次使用、正常、过滤空态和错误重试", async () => {
    const store = usePromptConfigStore();
    await store.load();
    expect(store.state).toBe("first_use");

    aiApi.listPromptProfiles.mockResolvedValueOnce(result({
      items: [promptProfileFixture()],
      totalKnown: 1
    }));
    await store.load();
    expect(store.state).toBe("ready");

    store.search = "不存在";
    store.recomputeState();
    expect(store.state).toBe("filtered_empty");
    store.clearFilters();
    expect(store.state).toBe("ready");

    vi.spyOn(console, "error").mockImplementation(() => undefined);
    aiApi.listPromptProfiles.mockRejectedValueOnce(
      new RuntimeError("Prompt 列表不可用。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-prompt",
        status: 503
      })
    );
    await store.load();
    expect(store.state).toBe("error");
    expect(store.error?.logId).toBe("log-prompt");

    aiApi.listPromptProfiles.mockResolvedValueOnce(result({
      items: [promptProfileFixture()],
      totalKnown: 1
    }));
    await store.load();
    expect(store.state).toBe("ready");
  });

  it("Prompt 正文只在主动打开后按版本加载并进入只读态", async () => {
    const store = usePromptConfigStore();
    store.profiles = [promptProfileFixture()];
    store.state = "ready";
    store.selectProfile("script-default");
    aiApi.getPromptVersion.mockResolvedValueOnce(result(promptVersionFixture()));

    expect(store.selectedBody).toBeNull();
    expect(store.editorState).toBe("summary");

    await store.openSelectedBody();
    expect(aiApi.getPromptVersion).toHaveBeenCalledWith(
      "script-default",
      1,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(store.editorState).toBe("view");
    expect(store.selectedBody?.id).toBe("prompt-version-1");
  });

  it("新建 Prompt Profile 保存 JSON 对象并保留原激活版本策略", async () => {
    const store = usePromptConfigStore();
    store.beginCreateProfile();
    store.updateDraft("profileKey", "script-account");
    store.updateDraft("name", "账号脚本 Prompt");
    store.updateDraft("systemPrompt", "你是脚本策划。");
    store.updateDraft("taskTemplate", "生成 {{topic}} 脚本。");
    store.updateDraft("variablesSchema", "{\"type\":\"object\"}");
    store.updateDraft("outputSchema", "{\"type\":\"object\"}");
    aiApi.createPromptProfile.mockResolvedValueOnce(result(
      promptProfileFixture({
        profileKey: "script-account",
        name: "账号脚本 Prompt",
        activeVersion: null,
        activeVersionId: null,
        versions: [{
          version: 1,
          status: "draft",
          contentHash: "d".repeat(64)
        }],
        referenceCount: 0,
        revision: 1
      }),
      201
    ));
    aiApi.listPromptProfiles.mockResolvedValueOnce(result({
      items: [promptProfileFixture({
        profileKey: "script-account",
        activeVersion: null,
        activeVersionId: null
      })],
      totalKnown: 1
    }));

    expect(await store.saveDraft()).toBe(true);
    expect(aiApi.createPromptProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        profileKey: "script-account",
        variablesSchema: { type: "object" },
        outputSchema: { type: "object" }
      }),
      expect.objectContaining({
        idempotencyKey: expect.stringContaining(
          "prompt-profile-create:script-account:"
        )
      })
    );
    expect(store.dirty).toBe(false);
    expect(store.feedback).toContain("原激活版本未被改写");
  });

  it("Prompt 新版本和激活分别使用 Profile 修订锁", async () => {
    const store = usePromptConfigStore();
    const profile = promptProfileFixture({ revision: 6 });
    const source = promptVersionFixture();
    store.profiles = [profile];
    store.selectedProfileKey = profile.profileKey;
    store.selectedVersion = 1;
    store.bodyByVersion["script-default@1"] = source;
    store.beginCreateVersion();
    store.updateDraft("name", "脚本 Prompt v2");
    aiApi.createPromptVersion.mockResolvedValueOnce(result(
      promptVersionFixture({
        id: "prompt-version-2",
        name: "脚本 Prompt v2",
        version: 2,
        status: "draft",
        createdFromId: "prompt-version-1",
        revision: 1
      }),
      201
    ));
    aiApi.listPromptProfiles.mockResolvedValueOnce(result({
      items: [promptProfileFixture({ revision: 7 })],
      totalKnown: 1
    }));

    expect(await store.saveDraft()).toBe(true);
    expect(aiApi.createPromptVersion).toHaveBeenCalledWith(
      "script-default",
      expect.objectContaining({ createdFromVersion: 1 }),
      expect.objectContaining({ expectedRevision: 6 })
    );

    store.profiles = [promptProfileFixture({ revision: 7 })];
    store.selectedProfileKey = "script-default";
    store.selectedVersion = 2;
    aiApi.activatePromptVersion.mockResolvedValueOnce(result(
      promptProfileFixture({
        activeVersion: 2,
        activeVersionId: "prompt-version-2",
        revision: 8
      })
    ));
    aiApi.listPromptProfiles.mockResolvedValueOnce(result({
      items: [promptProfileFixture({
        activeVersion: 2,
        activeVersionId: "prompt-version-2",
        revision: 8
      })],
      totalKnown: 1
    }));

    expect(await store.activateSelectedVersion()).toBe(true);
    expect(aiApi.activatePromptVersion).toHaveBeenCalledWith(
      "script-default",
      2,
      expect.objectContaining({ expectedRevision: 7 })
    );
  });

  it("Prompt 非对象 JSON 在本地进入错误态且不发出写请求", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const store = usePromptConfigStore();
    store.beginCreateProfile();
    store.updateDraft("variablesSchema", "[]");

    expect(await store.saveDraft()).toBe(false);
    expect(store.state).toBe("error");
    expect(store.error?.message).toContain("变量 Schema必须是 JSON 对象");
    expect(aiApi.createPromptProfile).not.toHaveBeenCalled();
  });

  it("合成模板覆盖首次使用、正常、过滤空态和错误重试", async () => {
    const store = useCompositionTemplateStore();
    await store.load();
    expect(store.state).toBe("first_use");

    aiApi.listCompositionTemplates.mockResolvedValueOnce(result({
      items: [compositionTemplateFixture()],
      totalKnown: 1
    }));
    await store.load();
    expect(store.state).toBe("ready");

    store.search = "不存在";
    store.recomputeState();
    expect(store.state).toBe("filtered_empty");

    vi.spyOn(console, "error").mockImplementation(() => undefined);
    aiApi.listCompositionTemplates.mockRejectedValueOnce(
      new RuntimeError("合成模板不可用。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-template",
        status: 503
      })
    );
    await store.load();
    expect(store.state).toBe("error");
    expect(store.error?.logId).toBe("log-template");
  });

  it("合成模板正文按需读取并从不可变来源创建新版本", async () => {
    const store = useCompositionTemplateStore();
    const template = compositionTemplateFixture({ revision: 4 });
    store.templates = [template];
    store.state = "ready";
    store.selectTemplate("mixed-default");
    aiApi.getCompositionTemplateVersion.mockResolvedValueOnce(
      result(compositionVersionFixture())
    );

    await store.openSelectedBody();
    expect(store.selectedBody?.id).toBe("composition-version-1");

    store.beginCreateVersion();
    store.updateDraft("name", "批量混合媒体 v2");
    aiApi.createCompositionTemplateVersion.mockResolvedValueOnce(result(
      compositionVersionFixture({
        id: "composition-version-2",
        name: "批量混合媒体 v2",
        version: 2,
        status: "draft",
        createdFromId: "composition-version-1"
      }),
      201
    ));
    aiApi.listCompositionTemplates.mockResolvedValueOnce(result({
      items: [compositionTemplateFixture({ revision: 5 })],
      totalKnown: 1
    }));

    expect(await store.saveDraft()).toBe(true);
    expect(aiApi.createCompositionTemplateVersion).toHaveBeenCalledWith(
      "mixed-default",
      expect.objectContaining({
        createdFromVersion: 1,
        aspectRatios: ["9:16"]
      }),
      expect.objectContaining({ expectedRevision: 4 })
    );
  });

  it("合成模板必须先验证再以修订锁激活选定版本", async () => {
    const store = useCompositionTemplateStore();
    store.templates = [compositionTemplateFixture({ revision: 8 })];
    store.selectedTemplateKey = "mixed-default";
    store.selectedVersion = 1;
    aiApi.validateCompositionTemplateVersion.mockResolvedValueOnce(result({
      templateKey: "mixed-default",
      version: 1,
      validationStatus: "valid",
      validationIssues: [],
      verifiedCapabilities: ["text_to_video"],
      checkedAt: "2026-07-26T10:05:00Z"
    }));

    expect(await store.validateSelectedVersion()).toBe(true);
    expect(store.selectedValidation?.validationStatus).toBe("valid");

    aiApi.activateCompositionTemplateVersion.mockResolvedValueOnce(
      result(compositionTemplateFixture())
    );
    aiApi.listCompositionTemplates.mockResolvedValueOnce(result({
      items: [compositionTemplateFixture({ revision: 9 })],
      totalKnown: 1
    }));
    expect(await store.activateSelectedVersion()).toBe(true);
    expect(aiApi.activateCompositionTemplateVersion).toHaveBeenCalledWith(
      "mixed-default",
      1,
      expect.objectContaining({ expectedRevision: 8 })
    );
  });
});
