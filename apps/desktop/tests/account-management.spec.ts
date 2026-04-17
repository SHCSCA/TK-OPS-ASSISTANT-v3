import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountManagementPage from "@/pages/accounts/AccountManagementPage.vue";
import { useShellUiStore } from "@/stores/shell-ui";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("账号管理页面体验", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("展示真实账号对象并在选中后同步打开绑定详情上下文", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/accounts" && method === "GET") {
          return okJsonResponse([accountFixture()]);
        }
        if (path === "/api/accounts/groups" && method === "GET") {
          return okJsonResponse([groupFixture()]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, shellUiStore } = mountAccountPage();
    await flushPromises();

    expect(wrapper.text()).toContain("账号管理");
    expect(wrapper.text()).toContain("主账号");
    expect(wrapper.text()).toContain("主账号组");

    await wrapper.get('[data-testid="account-card-acc-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="account-card-acc-1"]').classes()).toContain("account-card--selected");
    expect(shellUiStore.isDetailPanelOpen).toBe(true);
    expect(shellUiStore.detailContext.title).toBe("主账号");
    expect(shellUiStore.detailContext.sections.some((section) => section.title === "分组与绑定")).toBe(true);
  });

  it("当 Runtime 不返回分组时显示 blocked 提示且仍只展示真实账号对象", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/accounts" && method === "GET") {
          return okJsonResponse([accountFixture("acc-2", "备用账号", "inactive")]);
        }
        if (path === "/api/accounts/groups" && method === "GET") {
          return okJsonResponse([]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = mountAccountPage();
    await flushPromises();

    expect(wrapper.text()).toContain("Runtime 尚未返回账号分组目录");
    expect(wrapper.text()).toContain("备用账号");
    expect(wrapper.text()).toContain("不会伪造绑定关系");
  });
});

function mountAccountPage() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(AccountManagementPage, {
    global: {
      plugins: [pinia]
    }
  });

  return {
    wrapper,
    shellUiStore: useShellUiStore()
  };
}

function now() {
  return "2026-04-16T10:00:00Z";
}

function accountFixture(
  id = "acc-1",
  name = "主账号",
  status = "active"
) {
  return {
    id,
    name,
    platform: "tiktok",
    username: "creator_main",
    avatarUrl: null,
    status,
    authExpiresAt: "2026-04-30T00:00:00Z",
    followerCount: 12345,
    followingCount: 128,
    videoCount: 42,
    tags: '["主账号", "发布"]',
    notes: "真实发布账号",
    createdAt: now(),
    updatedAt: now()
  };
}

function groupFixture() {
  return {
    id: "group-1",
    name: "主账号组",
    description: "用于真实筛选",
    color: null,
    createdAt: now()
  };
}
