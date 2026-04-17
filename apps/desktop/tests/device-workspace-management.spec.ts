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
    created_at: now(),
    updated_at: now()
  };
}
