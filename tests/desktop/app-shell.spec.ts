import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

describe("App shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all formal routes and shows runtime health", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ok: true,
          data: {
            service: "online",
            version: "0.1.1",
            now: "2026-04-11T00:00:00Z",
            mode: "development"
          }
        })
      })
    );

    const pinia = createPinia();
    const router = createAppRouter(createMemoryHistory());
    router.push("/dashboard");
    await router.isReady();

    const wrapper = mount(App, {
      global: {
        plugins: [pinia, router]
      }
    });

    await flushPromises();

    expect(wrapper.findAll("[data-route-id]")).toHaveLength(16);
    expect(wrapper.text()).toContain("创作总览");
    expect(wrapper.text()).toContain("Runtime 在线");
  });
});
