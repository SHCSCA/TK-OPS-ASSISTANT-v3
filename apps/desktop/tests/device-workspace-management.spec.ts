import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DeviceWorkspaceManagementPage from "@/pages/devices/DeviceWorkspaceManagementPage.vue";
import { useShellUiStore } from "@/stores/shell-ui";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("设备与工作区管理页面体验", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("展示真实工作区对象并在选中后同步打开执行边界详情", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/devices/workspaces" && method === "GET") {
          return okJsonResponse([workspaceFixture()]);
        }
        if (path === "/api/devices/workspaces/ws-1/browser-instances" && method === "GET") {
          return okJsonResponse([browserInstanceFixture()]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, shellUiStore } = mountDevicePage();
    await flushPromises();

    expect(wrapper.text()).toContain("设备与工作区管理");
    expect(wrapper.text()).toContain("PC-01 工作区");
    expect(wrapper.text()).toContain("浏览器实例");

    await wrapper.get('[data-testid="workspace-card-ws-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-card-ws-1"]').classes()).toContain("workspace-card--selected");
    expect(shellUiStore.isDetailPanelOpen).toBe(true);
    expect(shellUiStore.detailContext.title).toBe("PC-01 工作区");
    expect(shellUiStore.detailContext.sections.some((section) => section.title === "执行绑定")).toBe(true);
    expect(wrapper.text()).toContain("默认浏览器");
    expect(wrapper.text()).toContain("Data/Profile-01");
  });

  it("通过工作区嵌套路由创建真实浏览器实例", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });
        if (path === "/api/devices/workspaces" && method === "GET") {
          return okJsonResponse([workspaceFixture()]);
        }
        if (path === "/api/devices/workspaces/ws-1/browser-instances" && method === "GET") {
          return okJsonResponse([]);
        }
        if (path === "/api/devices/workspaces/ws-1/browser-instances" && method === "POST") {
          return okJsonResponse(browserInstanceFixture());
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = mountDevicePage();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-card-ws-1"]').trigger("click");
    await flushPromises();
    await wrapper.get(".detail-block button").trigger("click");
    await wrapper.get('input[placeholder="例：Profile-01"]').setValue("默认浏览器");
    await wrapper.get('input[placeholder="Data/Profile-01"]').setValue("Data/Profile-01");
    await wrapper.get("form.drawer-form").trigger("submit");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/devices/workspaces/ws-1/browser-instances",
      method: "POST",
      body: {
        name: "默认浏览器",
        profilePath: "Data/Profile-01"
      }
    });
    expect(wrapper.text()).toContain("默认浏览器");
  });

  it("当 Runtime 没有工作区时显示 empty 与 blocked 说明", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/devices/workspaces" && method === "GET") {
          return okJsonResponse([]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = mountDevicePage();
    await flushPromises();

    expect(wrapper.text()).toContain("没有返回工作区对象");
    expect(wrapper.text()).toContain("不会伪造设备在线率或浏览器实例");
    expect(wrapper.text()).toContain("没有符合条件的工作区");
  });
});

function mountDevicePage() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(DeviceWorkspaceManagementPage, {
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

function workspaceFixture() {
  return {
    id: "ws-1",
    name: "PC-01 工作区",
    root_path: "C:/Users/pc01/TK-Workspace",
    status: "online",
    error_count: 0,
    last_used_at: "2026-04-16T09:00:00Z",
    environmentStatus: {
      status: "ready",
      rootPathExists: true,
      isDirectory: true,
      browserInstanceCount: 1,
      runningBrowserInstanceCount: 0,
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    bindingSummary: {
      totalBindings: 0,
      activeBindings: 0,
      accountIds: []
    },
    healthSummary: {
      status: "unknown",
      checkedAt: null,
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    created_at: now(),
    updated_at: now()
  };
}

function browserInstanceFixture() {
  return {
    id: "browser-1",
    workspaceId: "ws-1",
    name: "默认浏览器",
    profilePath: "Data/Profile-01",
    status: "ready",
    lastCheckedAt: now(),
    lastStartedAt: null,
    lastStoppedAt: null,
    errorCode: null,
    errorMessage: null,
    createdAt: now(),
    updatedAt: now()
  };
}
