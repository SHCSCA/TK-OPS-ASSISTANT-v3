import { mount } from "@vue/test-utils";
import {
  createMemoryHistory,
  createRouter
} from "vue-router";
import { describe, expect, it } from "vitest";

import AccountCapabilityPendingPage from "@/pages/workspace-home/AccountCapabilityPendingPage.vue";

describe("P0 未迁移能力受限态", () => {
  it.each([
    ["p1_pending", "P1 创作阶段", "尚未接入生产 Runtime"],
    ["p2_pending", "P2 交付阶段", "尚未接入生产 Runtime"]
  ])("明确展示 %s 阶段，不伪造业务结果", async (
    migrationState,
    stageLabel,
    message
  ) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{
        path: "/pending",
        component: AccountCapabilityPendingPage,
        meta: {
          migrationState,
          routeId: migrationState === "p1_pending"
            ? "account_script_topic"
            : "account_publishing",
          title: migrationState === "p1_pending"
            ? "脚本与选题"
            : "发布"
        }
      }]
    });
    await router.push("/pending");
    await router.isReady();
    const wrapper = mount(AccountCapabilityPendingPage, {
      global: {
        plugins: [router]
      }
    });

    expect(wrapper.attributes("data-state")).toBe(migrationState);
    expect(wrapper.text()).toContain(stageLabel);
    expect(wrapper.text()).toContain(message);
    expect(wrapper.text()).not.toContain("已生成");
    wrapper.unmount();
  });
});
