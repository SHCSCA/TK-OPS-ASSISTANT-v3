import { nextTick } from "vue";
import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";
import {
  createMemoryHistory,
  createRouter
} from "vue-router";
import { describe, expect, it } from "vitest";

import P0BootstrapGate from "@/bootstrap/P0BootstrapGate.vue";
import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";

describe("P0 启动门禁", () => {
  it("启动检查完成前不挂载账号工作区壳", async () => {
    const { pinia, router } = await createGateRouter("/workspace");
    const store = useP0BootstrapStore(pinia);
    store.phase = "loading";
    const wrapper = shallowMount(P0BootstrapGate, {
      global: {
        plugins: [pinia, router]
      }
    });

    expect(wrapper.findComponent({ name: "BootstrapLoadingScreen" }).exists())
      .toBe(true);
    expect(wrapper.findComponent({ name: "AccountWorkspaceLayout" }).exists())
      .toBe(false);

    store.phase = "ready";
    await nextTick();

    expect(wrapper.findComponent({ name: "AccountWorkspaceLayout" }).exists())
      .toBe(true);
    wrapper.unmount();
  });

  it("首启路由始终保持独立 RouterView，不加载账号工作区壳", async () => {
    const { pinia, router } = await createGateRouter("/setup/license");
    const store = useP0BootstrapStore(pinia);
    store.phase = "setup_required";
    const wrapper = shallowMount(P0BootstrapGate, {
      global: {
        plugins: [pinia, router],
        stubs: {
          RouterView: {
            name: "RouterView",
            template: '<section data-testid="setup-router-view" />'
          }
        }
      }
    });

    expect(wrapper.get('[data-testid="setup-router-view"]').exists()).toBe(true);
    expect(wrapper.findComponent({ name: "AccountWorkspaceLayout" }).exists())
      .toBe(false);
    wrapper.unmount();
  });

  it("Supervisor 允许恢复时向错误页提供重启动作", async () => {
    const { pinia, router } = await createGateRouter("/workspace");
    const store = useP0BootstrapStore(pinia);
    store.phase = "error";
    store.error = {
      code: "RUNTIME_OFFLINE",
      message: "本机 Runtime 已离线。",
      logId: "log-runtime",
      requestId: null,
      retryable: true
    };
    store.supervisorStatus = {
      status: "offline",
      phase: "monitoring",
      baseUrl: null,
      errorCode: "RUNTIME_EXITED",
      generation: 2,
      logId: "log-runtime",
      restartAttempt: 1,
      maxRestartAttempts: 2,
      canRestart: true,
      updatedAtEpochMs: Date.now()
    };
    const wrapper = shallowMount(P0BootstrapGate, {
      global: {
        plugins: [pinia, router]
      }
    });
    const errorScreen = wrapper.getComponent({
      name: "BootstrapErrorScreen"
    });

    expect(errorScreen.props("canRestart")).toBe(true);
    expect(errorScreen.props("errorSummary")).toContain("log-runtime");
    wrapper.unmount();
  });
});

async function createGateRouter(path: string) {
  const pinia = createPinia();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/workspace",
        name: "account_workspace_home",
        component: { template: "<section />" }
      },
      {
        path: "/setup/license",
        name: "setup_license_wizard",
        component: { template: "<section />" }
      }
    ]
  });
  await router.push(path);
  await router.isReady();
  return { pinia, router };
}
