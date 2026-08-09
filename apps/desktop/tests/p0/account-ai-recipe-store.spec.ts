import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RuntimeError } from "@/app/runtime-client/core";

import {
  compositionTemplateFixture,
  recipeFixture,
  recipeValidationFixture,
  recipeVersionFixture,
  result
} from "./ai-system-fixtures";

const recipeApi = vi.hoisted(() => ({
  activateAccountAIRecipeVersion: vi.fn(),
  createAccountAIRecipeVersion: vi.fn(),
  getAccountAIRecipe: vi.fn(),
  listAccountAIRecipeVersions: vi.fn(),
  validateAccountAIRecipeVersion: vi.fn()
}));
const aiApi = vi.hoisted(() => ({
  listCompositionTemplates: vi.fn()
}));

vi.mock("@/app/runtime-client/account-ai-recipe", () => recipeApi);
vi.mock("@/app/runtime-client/ai-system", () => aiApi);

import { useAccountAIRecipeStore } from "@/modules/ai-recipes/account-ai-recipe-store";

describe("P0-E 账号 AI Recipe store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
    recipeApi.getAccountAIRecipe.mockResolvedValue(result(
      recipeFixture({ activeVersion: null, versions: [] })
    ));
    recipeApi.listAccountAIRecipeVersions.mockResolvedValue(result({
      items: [],
      totalKnown: 0
    }));
    aiApi.listCompositionTemplates.mockResolvedValue(result({
      items: [],
      totalKnown: 0
    }));
  });

  it("真实加载过程从 loading 进入首次使用空态", async () => {
    const pending = deferred<ReturnType<typeof result>>();
    recipeApi.getAccountAIRecipe.mockReturnValueOnce(pending.promise);
    const store = useAccountAIRecipeStore();

    const loading = store.load("account-1");
    expect(store.cache("account-1").state).toBe("loading");
    pending.resolve(result(recipeFixture({
      activeVersion: null,
      versions: []
    })));
    await loading;

    expect(store.cache("account-1").state).toBe("first_use");
    expect(store.visibleAccountId).toBe("account-1");
  });

  it("加载真实版本并只保留已激活版本 ID 的合成模板", async () => {
    mockRecipeLoad({
      recipe: recipeFixture(),
      versions: [recipeVersionFixture()],
      templates: [
        compositionTemplateFixture(),
        compositionTemplateFixture({
          templateKey: "draft-template",
          activeVersion: null,
          activeVersionId: null,
          versions: [{
            version: 1,
            status: "draft",
            contentHash: "d".repeat(64)
          }]
        })
      ]
    });
    const store = useAccountAIRecipeStore();

    await store.load("account-1");

    const cache = store.cache("account-1");
    expect(cache.state).toBe("ready");
    expect(cache.versions).toHaveLength(1);
    expect(cache.templates).toEqual([
      expect.objectContaining({
        templateKey: "mixed-default",
        activeVersionId: "composition-version-1"
      })
    ]);
  });

  it("未激活或未验证版本进入依赖阻塞态", async () => {
    mockRecipeLoad({
      recipe: recipeFixture({
        activeVersion: null,
        versions: [{
          version: 1,
          status: "draft",
          validationStatus: "unvalidated"
        }]
      }),
      versions: [recipeVersionFixture({
        status: "draft",
        validationStatus: "unvalidated"
      })],
      templates: [compositionTemplateFixture()]
    });
    const store = useAccountAIRecipeStore();

    await store.load("account-1");
    expect(store.cache("account-1").state).toBe("dependency_blocked");
  });

  it("账号切换后迟到响应只写入自身缓存，不污染当前账号", async () => {
    const accountOne = deferred<ReturnType<typeof result>>();
    recipeApi.getAccountAIRecipe
      .mockReturnValueOnce(accountOne.promise)
      .mockResolvedValueOnce(result(recipeFixture({
        accountId: "account-2",
        activeVersion: null,
        versions: []
      })));
    recipeApi.listAccountAIRecipeVersions.mockImplementation(
      (accountId: string) => result({
        items: accountId === "account-1" ? [recipeVersionFixture()] : [],
        totalKnown: accountId === "account-1" ? 1 : 0
      })
    );
    const store = useAccountAIRecipeStore();

    const staleLoad = store.load("account-1");
    await store.load("account-2");
    accountOne.resolve(result(recipeFixture()));
    await staleLoad;

    expect(store.visibleAccountId).toBe("account-2");
    expect(store.cache("account-2").state).toBe("first_use");
    expect(store.cache("account-1").recipe).toEqual(
      expect.objectContaining({ accountId: "account-1" })
    );
  });

  it("新版本保存使用账号 Recipe 修订并传递合成模板版本行 ID", async () => {
    const store = useAccountAIRecipeStore();
    const cache = store.cache("account-1");
    cache.recipe = recipeFixture({ revision: 7 });
    cache.templates = [compositionTemplateFixture()];
    store.beginCreateVersion("account-1");
    store.updateDraft("account-1", "name", "账号口播配方");
    store.updateDraft(
      "account-1",
      "compositionTemplateRef",
      "composition-version-1"
    );
    store.updateDraft(
      "account-1",
      "routeOverrides",
      "{\"script_generation\":{\"modelProfileId\":\"model-1\"}}"
    );
    recipeApi.createAccountAIRecipeVersion.mockResolvedValueOnce(result(
      recipeVersionFixture({
        id: "recipe-version-2",
        version: 2,
        status: "draft",
        name: "账号口播配方",
        validationStatus: "unvalidated"
      }),
      201
    ));
    mockRecipeLoad({
      recipe: recipeFixture({
        activeVersion: 1,
        revision: 8,
        versions: [
          ...recipeFixture().versions,
          {
            version: 2,
            status: "draft",
            validationStatus: "unvalidated"
          }
        ]
      }),
      versions: [
        recipeVersionFixture(),
        recipeVersionFixture({
          id: "recipe-version-2",
          version: 2,
          status: "draft",
          validationStatus: "unvalidated"
        })
      ],
      templates: [compositionTemplateFixture()]
    });

    expect(await store.saveDraft("account-1")).toBe(true);
    expect(recipeApi.createAccountAIRecipeVersion).toHaveBeenCalledWith(
      "account-1",
      expect.objectContaining({
        name: "账号口播配方",
        compositionTemplateRef: "composition-version-1",
        routeOverrides: {
          script_generation: { modelProfileId: "model-1" }
        }
      }),
      expect.objectContaining({
        expectedRevision: 7,
        idempotencyKey: expect.stringContaining(
          "account-recipe-version-create:account-1:"
        )
      })
    );
    expect(cache.dirty).toBe(false);
    expect(cache.editorOpen).toBe(false);
  });

  it("无效 JSON 在本地反馈错误并保留编辑草稿", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const store = useAccountAIRecipeStore();
    const cache = store.cache("account-1");
    cache.recipe = recipeFixture();
    store.beginCreateVersion("account-1");
    store.updateDraft("account-1", "visualStyle", "[]");

    expect(await store.saveDraft("account-1")).toBe(false);
    expect(cache.state).toBe("error");
    expect(cache.error?.message).toContain("视觉风格必须是 JSON 对象");
    expect(cache.dirty).toBe(true);
    expect(cache.editorOpen).toBe(true);
    expect(recipeApi.createAccountAIRecipeVersion).not.toHaveBeenCalled();
  });

  it("验证结果保留解析路由，只有有效版本才进入激活请求", async () => {
    const store = useAccountAIRecipeStore();
    const cache = store.cache("account-1");
    cache.recipe = recipeFixture({ revision: 9 });
    cache.versions = [recipeVersionFixture()];
    recipeApi.validateAccountAIRecipeVersion.mockResolvedValueOnce(
      result(recipeValidationFixture())
    );
    mockRecipeLoad({
      recipe: recipeFixture({ revision: 9 }),
      versions: [recipeVersionFixture()],
      templates: [compositionTemplateFixture()]
    });

    expect(await store.validateVersion("account-1", 1)).toBe(true);
    expect(cache.validation?.resolvedRouteSummary.script_generation).toEqual({
      modelProfileId: "model-1",
      promptProfileId: "prompt-version-1",
      source: "system"
    });

    recipeApi.activateAccountAIRecipeVersion.mockResolvedValueOnce(
      result(recipeFixture({ revision: 10 }))
    );
    mockRecipeLoad({
      recipe: recipeFixture({ revision: 10 }),
      versions: [recipeVersionFixture()],
      templates: [compositionTemplateFixture()]
    });
    expect(await store.activateVersion("account-1", 1)).toBe(true);
    expect(recipeApi.activateAccountAIRecipeVersion).toHaveBeenCalledWith(
      "account-1",
      1,
      expect.objectContaining({
        expectedRevision: 9,
        idempotencyKey: expect.stringContaining(
          "account-recipe-activate:account-1:"
        )
      })
    );
  });

  it("编辑草稿接入保存与放弃未保存协议", async () => {
    const store = useAccountAIRecipeStore();
    const cache = store.cache("account-1");
    cache.recipe = recipeFixture();
    store.beginCreateVersion("account-1", recipeVersionFixture());
    store.updateDraft("account-1", "name", "待保存配方");
    expect(cache.dirty).toBe(true);

    store.discardDraft("account-1");
    expect(cache.dirty).toBe(false);
    expect(cache.editorOpen).toBe(false);
    expect(cache.draft.name).toBe("");

    store.beginCreateVersion("account-1");
    store.updateDraft("account-1", "name", "保存失败配方");
    vi.spyOn(store, "saveDraft").mockResolvedValueOnce(false);
    await expect(store.saveUnsaved("account-1")).rejects.toThrow(
      "账号 AI Recipe 保存失败"
    );
  });

  it("Runtime 错误映射为可重试错误并支持重新加载", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    recipeApi.getAccountAIRecipe.mockRejectedValueOnce(
      new RuntimeError("Recipe 服务暂不可用。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-recipe",
        status: 503
      })
    );
    const store = useAccountAIRecipeStore();

    await store.load("account-1");
    expect(store.cache("account-1").error).toMatchObject({
      message: "Recipe 服务暂不可用。",
      logId: "log-recipe",
      retryable: true
    });

    mockRecipeLoad({
      recipe: recipeFixture(),
      versions: [recipeVersionFixture()],
      templates: [compositionTemplateFixture()]
    });
    await store.load("account-1");
    expect(store.cache("account-1").state).toBe("ready");
    expect(store.cache("account-1").error).toBeNull();
  });
});

function mockRecipeLoad(input: {
  recipe: ReturnType<typeof recipeFixture>;
  versions: ReturnType<typeof recipeVersionFixture>[];
  templates: ReturnType<typeof compositionTemplateFixture>[];
}): void {
  recipeApi.getAccountAIRecipe.mockResolvedValueOnce(result(input.recipe));
  recipeApi.listAccountAIRecipeVersions.mockResolvedValueOnce(result({
    items: input.versions,
    totalKnown: input.versions.length
  }));
  aiApi.listCompositionTemplates.mockResolvedValueOnce(result({
    items: input.templates,
    totalKnown: input.templates.length
  }));
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}
