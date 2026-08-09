import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountCopyConfigDialog from "@/modules/accounts/components/AccountCopyConfigDialog.vue";
import AccountDetailPanel from "@/modules/accounts/components/AccountDetailPanel.vue";
import AccountAIRecipePanel from "@/modules/ai-recipes/components/AccountAIRecipePanel.vue";

import {
  accountFixture,
  compositionTemplateFixture,
  recipeFixture,
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

describe("P0-E 账号 AI Recipe UI 接入", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    recipeApi.getAccountAIRecipe.mockResolvedValue(result(
      recipeFixture({ activeVersion: null, versions: [] })
    ));
    recipeApi.listAccountAIRecipeVersions.mockResolvedValue(result({
      items: [],
      totalKnown: 0
    }));
    aiApi.listCompositionTemplates.mockResolvedValue(result({
      items: [compositionTemplateFixture()],
      totalKnown: 1
    }));
  });

  it("首次使用可创建 Recipe，合成模板使用版本行 ID，关闭脏编辑器触发守卫", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(AccountAIRecipePanel, {
      global: { plugins: [pinia] },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    expect(wrapper.text()).toContain("创建首个 Recipe");
    await button(wrapper, "创建首个 Recipe").trigger("click");
    await wrapper.get('.recipe-editor input[maxlength="100"]').setValue(
      "账号口播配方"
    );
    await wrapper.get(".recipe-editor select").setValue(
      "composition-version-1"
    );
    expect(
      (wrapper.get(".recipe-editor select").element as HTMLSelectElement).value
    ).toBe("composition-version-1");

    await wrapper.get('[aria-label="关闭 AI Recipe 编辑器"]').trigger("click");
    expect(wrapper.text()).toContain("处理未保存配置");
    expect(wrapper.text()).toContain("账号 AI Recipe包含未保存内容");
    await button(wrapper, "放弃并继续").trigger("click");
    expect(wrapper.find(".recipe-editor").exists()).toBe(false);
  });

  it("账号详情的 AI 创作档案接入真实 Recipe 面板并正确解释模板引用", async () => {
    recipeApi.getAccountAIRecipe.mockResolvedValueOnce(result(recipeFixture()));
    recipeApi.listAccountAIRecipeVersions.mockResolvedValueOnce(result({
      items: [recipeVersionFixture()],
      totalKnown: 1
    }));
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(AccountDetailPanel, {
      global: { plugins: [pinia] },
      props: {
        account: accountFixture(),
        activeTab: "ai_recipe",
        busy: false
      }
    });
    await flushPromises();

    expect(wrapper.get('.recipe-panel[data-account-id="account-1"]')).toBeTruthy();
    expect(wrapper.text()).toContain("AI Recipe");
    expect(wrapper.text()).toContain("默认混合媒体模板 · v1");
    expect(wrapper.text()).not.toContain("等待 P0-E AI 配方");
  });

  it("复制配置对话框提供 AI 配方分区并提交明确选择", async () => {
    const wrapper = mount(AccountCopyConfigDialog, {
      props: {
        accounts: [
          accountFixture(),
          accountFixture({ id: "account-2", name: "素材观察" })
        ],
        busy: false,
        open: true,
        target: accountFixture()
      }
    });

    expect(wrapper.text()).toContain("AI 配方");
    await wrapper.get("select").setValue("account-2");
    const aiRecipe = wrapper.findAll('input[type="checkbox"]').find(
      (input) => input.attributes("value") === "aiRecipe"
    );
    if (!aiRecipe) throw new Error("未找到 AI 配方复制选项");
    await aiRecipe.setValue(true);
    await button(wrapper, "开始复制").trigger("click");

    expect(wrapper.emitted("submit")?.[0]).toEqual([{
      sourceAccountId: "account-2",
      sections: ["aiRecipe"]
    }]);
  });
});

function button(wrapper: VueWrapper, label: string) {
  const match = wrapper.findAll("button").find(
    (candidate) => candidate.text().trim() === label
  );
  if (!match) throw new Error(`未找到按钮：${label}`);
  return match;
}
