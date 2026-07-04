import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import RenderExportCenterPage from "@/pages/renders/RenderExportCenterPage.vue";
import { useProjectStore } from "@/stores/project";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("M14 渲染与导出中心页面", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("展示 Runtime 返回的完成状态和真实输出路径", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/renders/tasks" && method === "GET") {
          return okJsonResponse([renderTask()]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const wrapper = await mountPageWithProject();
    await flushPromises();

    expect(wrapper.text()).toContain("渲染与导出中心");
    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).toContain("render-1.mp4");
    expect(wrapper.text()).toContain("G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports/project-1/render-1.mp4");
    expect(wrapper.text()).toContain("文件可打开");
    expect(wrapper.text()).toContain("1.0 KB");
    expect(wrapper.text()).not.toContain("未生成");
  });

  it("从 AI 剪辑工作台进入时显示项目和时间线交接上下文", async () => {
    vi.stubGlobal("fetch", createRenderTaskFetch([]));

    const wrapper = await mountPageWithProject(
      "/renders/export?from=workspace&projectId=project-1&timelineId=timeline-1"
    );
    await flushPromises();

    const handoff = wrapper.get('[data-testid="render-workspace-handoff"]');

    expect(handoff.text()).toContain("来自 AI 剪辑工作台");
    expect(handoff.text()).toContain("渲染交付项目");
    expect(handoff.text()).toContain("project-1");
    expect(handoff.text()).toContain("timeline-1");
    expect(handoff.text()).toContain("可以继续配置导出任务");
  });

  it("有效工作台交接创建任务时提交 timeline_id", async () => {
    const requests: Array<{ body: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, body) => {
        requests.push({ body, method, path });
        if (path === "/api/renders/tasks" && method === "GET") {
          return okJsonResponse([]);
        }
        if (path === "/api/renders/tasks" && method === "POST") {
          return okJsonResponse(renderTask({ timelineId: "timeline-1" }), { status: 201 });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const wrapper = await mountPageWithProject(
      "/renders/export?from=workspace&projectId=project-1&timelineId=timeline-1"
    );
    await flushPromises();

    await wrapper.get('[data-testid="render-create-task-button"]').trigger("click");
    const inputs = wrapper.findAll("input");
    expect(inputs[0].attributes("disabled")).toBeDefined();
    expect(inputs[1].attributes("disabled")).toBeDefined();
    await wrapper.get("form.drawer-form").trigger("submit");
    await flushPromises();

    const createRequest = requests.find((request) => request.method === "POST" && request.path === "/api/renders/tasks");
    const createPayload = JSON.parse(String((createRequest?.body as RequestInit | undefined)?.body ?? "{}"));

    expect(createPayload).toMatchObject({
      project_id: "project-1",
      project_name: "渲染交付项目",
      timeline_id: "timeline-1"
    });
    expect(wrapper.text()).toContain("timeline-1");
  });

  it("工作台交接缺少 timelineId 时显示阻断而不是假装可导出", async () => {
    vi.stubGlobal("fetch", createRenderTaskFetch([]));

    const wrapper = await mountPageWithProject("/renders/export?from=workspace&projectId=project-1");
    await flushPromises();

    const handoff = wrapper.get('[data-testid="render-workspace-handoff"]');

    expect(handoff.text()).toContain("交接信息不完整");
    expect(handoff.text()).toContain("回到 AI 剪辑工作台重新执行导出前预检");
    expect(handoff.text()).not.toContain("可以继续配置导出任务");
    expect(wrapper.get('[data-testid="render-create-task-button"]').attributes("disabled")).toBeDefined();
  });

  it("工作台交接项目与当前项目不一致时显示阻断", async () => {
    vi.stubGlobal("fetch", createRenderTaskFetch([]));

    const wrapper = await mountPageWithProject(
      "/renders/export?from=workspace&projectId=project-other&timelineId=timeline-1"
    );
    await flushPromises();

    const handoff = wrapper.get('[data-testid="render-workspace-handoff"]');

    expect(handoff.text()).toContain("项目上下文不一致");
    expect(handoff.text()).toContain("project-other");
    expect(handoff.text()).toContain("当前项目：project-1");
    expect(wrapper.get('[data-testid="render-create-task-button"]').attributes("disabled")).toBeDefined();
  });

  it("普通进入渲染中心时不显示工作台交接卡", async () => {
    vi.stubGlobal("fetch", createRenderTaskFetch([]));

    const wrapper = await mountPageWithProject("/renders/export");
    await flushPromises();

    expect(wrapper.find('[data-testid="render-workspace-handoff"]').exists()).toBe(false);
  });
});

async function mountPageWithProject(initialPath = "/renders/export") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const projectStore = useProjectStore();
  projectStore.currentProject = {
    projectId: "project-1",
    projectName: "渲染交付项目",
    status: "active"
  };
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/renders/export", component: RenderExportCenterPage }]
  });
  await router.push(initialPath);
  await router.isReady();

  return mount(RenderExportCenterPage, {
    global: {
      plugins: [pinia, router]
    }
  });
}

function createRenderTaskFetch(tasks: unknown[]) {
  return createRouteAwareFetch((path, method) => {
    if (path === "/api/renders/tasks" && method === "GET") {
      return okJsonResponse(tasks);
    }
    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function renderTask(input: { timelineId?: string | null } = {}) {
  const outputPath =
    "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports/project-1/render-1.mp4";
  return {
    id: "render-1",
    project_id: "project-1",
    project_name: "渲染交付项目",
    timeline_id: input.timelineId ?? null,
    preset: "1080p",
    format: "mp4",
    status: "completed",
    progress: 100,
    output_path: outputPath,
    error_code: null,
    error_message: null,
    stage: { code: "completed", label: "已完成" },
    output: {
      path: outputPath,
      exists: true,
      size_bytes: 1024,
      last_checked_at: now(),
      can_open: true
    },
    failure: { error_code: null, error_message: null, next_action: null, retryable: false },
    started_at: now(),
    finished_at: now(),
    created_at: now(),
    updated_at: now()
  };
}

function now() {
  return "2026-04-16T10:00:00Z";
}

class MockWebSocket {
  static readonly OPEN = 1;
  static readonly CONNECTING = 0;
  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor() {
    setTimeout(() => this.onopen?.(), 0);
  }

  send() {
    return undefined;
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}
