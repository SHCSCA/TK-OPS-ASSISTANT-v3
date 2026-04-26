import { flushPromises } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createRouteAwareFetch, mountApp, okJsonResponse, runtimeFixtures } from "./runtime-helpers";

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

describe("Script topic center", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to markdown preview and saves edited source content", async () => {
    const projectContext = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    const scriptDocument = {
      projectId: "project-001",
      currentVersion: {
        revision: 1,
        source: "manual",
        content: "Old hook\nOld body",
        provider: null,
        model: null,
        aiJobId: null,
        createdAt: "2026-04-11T10:20:00Z"
      },
      versions: [
        {
          revision: 1,
          source: "manual",
          content: "Old hook\nOld body",
          provider: null,
          model: null,
          aiJobId: null,
          createdAt: "2026-04-11T10:20:00Z"
        }
      ],
      recentJobs: []
    };

    const fetchMock = createRouteAwareFetch((path, method, init) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/context") {
        return okJsonResponse(projectContext);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [
            {
              id: "project-001",
              name: "Summer Launch",
              description: "Creator flow",
              status: "active",
              currentScriptVersion: 1,
              currentStoryboardVersion: 0,
              createdAt: "2026-04-11T10:00:00Z",
              updatedAt: "2026-04-11T10:20:00Z",
              lastAccessedAt: "2026-04-11T10:20:00Z"
            }
          ],
          currentProject: projectContext
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse(cloneValue(scriptDocument));
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "PUT") {
        const body = JSON.parse(String(init?.body)) as { content: string };
        scriptDocument.currentVersion = {
          revision: 2,
          source: "manual",
          content: body.content,
          provider: null,
          model: null,
          aiJobId: null,
          createdAt: "2026-04-11T10:25:00Z"
        };
        scriptDocument.versions = [scriptDocument.currentVersion, ...scriptDocument.versions];
        return okJsonResponse(cloneValue(scriptDocument));
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/scripts/topics");
    await flushPromises();

    expect(wrapper.find('[data-script-section="prompt-panel"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="versions"]').exists()).toBe(true);
    expect(wrapper.find('[data-script-section="title-variants"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("策划工作台");
    expect(wrapper.text()).toContain("视频主题");
    expect(wrapper.text()).toContain("产品/服务");
    expect(wrapper.text()).toContain("目标用户");
    expect(wrapper.text()).toContain("禁止内容");
    expect(wrapper.text()).toContain("结构锚点");
    expect(wrapper.get("[data-script-preview]").text()).toContain("Old hook");
    expect(wrapper.get("[data-script-preview]").text()).toContain("Old body");

    await wrapper.get('[data-editor-mode="source"]').trigger("click");
    const sourceInput = wrapper.get('[data-script-source-input] textarea');
    await sourceInput.setValue("# New hook\n\nNew body\nCTA");
    await wrapper.get('[data-action="save-script"]').trigger("click");
    await flushPromises();

    const saveCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/scripts/projects/project-001/document") && options?.method === "PUT"
    );

    expect(saveCall).toBeTruthy();
    expect(JSON.parse(String(saveCall?.[1]?.body))).toEqual({
      content: "# New hook\n\nNew body\nCTA"
    });

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("修订 2");
      expect(wrapper.findAll('[data-script-version-item]')).toHaveLength(2);
      expect(wrapper.text()).toContain("当前主标题");
    });
  });

  it("submits structured planning fields when generating scripts", async () => {
    const projectContext = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    const scriptDocument = {
      projectId: "project-001",
      currentVersion: null,
      versions: [],
      recentJobs: []
    };

    const fetchMock = createRouteAwareFetch((path, method, init) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/context") {
        return okJsonResponse(projectContext);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [],
          currentProject: projectContext
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse(cloneValue(scriptDocument));
      }
      if (path === "/api/scripts/projects/project-001/generate" && method === "POST") {
        const body = JSON.parse(String(init?.body)) as { topic: string };
        scriptDocument.currentVersion = {
          revision: 1,
          source: "ai_generate",
          content: "# 生成结果",
          provider: "deepseek",
          model: "deepseek-chat",
          aiJobId: "job-001",
          createdAt: "2026-04-25T09:20:00Z"
        };
        scriptDocument.versions = [scriptDocument.currentVersion];
        return okJsonResponse({ ...cloneValue(scriptDocument), submittedTopic: body.topic });
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/scripts/topics");
    await flushPromises();

    await wrapper.get('[data-planning-field="videoTheme"] input').setValue("春日咖啡冷饮");
    await wrapper.get('[data-planning-field="productService"] input').setValue("冰霸杯");
    await wrapper.get('[data-planning-field="targetUsers"] input').setValue("办公室人群");
    await wrapper.get('[data-planning-field="videoGoal"] select').setValue("种草");
    await wrapper.get('[data-planning-field="duration"] select').setValue("30秒");
    await wrapper.get('[data-planning-field="accountPositioning"] select').setValue("种草号");
    await wrapper.get('[data-planning-field="videoStyle"] select').setValue("真实口播");
    await wrapper.get('[data-planning-field="shootingConditions"] select').setValue("产品实拍");
    await wrapper.get('[data-planning-field="languageRequirement"] select').setValue("中文");
    await wrapper.get('[data-planning-field="forbiddenContent"] textarea').setValue("不要夸大承诺");
    await wrapper.get('[data-action="generate-script"]').trigger("click");
    await flushPromises();

    const generateCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        String(url).includes("/api/scripts/projects/project-001/generate") && options?.method === "POST"
    );
    const requestBody = JSON.parse(String(generateCall?.[1]?.body)) as { topic: string };

    expect(requestBody.topic).toContain("视频主题：春日咖啡冷饮");
    expect(requestBody.topic).toContain("产品/服务：冰霸杯");
    expect(requestBody.topic).toContain("目标用户：办公室人群");
    expect(requestBody.topic).toContain("视频目的：种草");
    expect(requestBody.topic).toContain("禁止内容：不要夸大承诺");
  });

  it("uses the same cleaned markdown for anchors and preview rendering", async () => {
    const projectContext = {
      projectId: "project-001",
      projectName: "Summer Launch",
      status: "active"
    };
    const scriptDocument = {
      projectId: "project-001",
      currentVersion: {
        revision: 2,
        source: "ai_rewrite",
        content: [
          "```markdown",
          "好的，没问题！我会先把这次改写目标收紧到年轻白领场景。",
          "",
          "---",
          "",
          "### 改写后脚本主题：工位“续命”杯",
          "",
          "* 核心卖点：超大容量、长效保冷。",
          "* 目标人群：年轻白领。",
          "",
          "---",
          "",
          "### 分镜脚本",
          "",
          "| 序号 | 画面内容 |",
          "| --- | --- |",
          "| 01 | 工位开场 |",
          "```"
        ].join("\n"),
        provider: "deepseek",
        model: "deepseek-chat",
        aiJobId: "job-002",
        createdAt: "2026-04-25T07:45:00Z"
      },
      versions: [],
      recentJobs: []
    };

    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/license/status") {
        return okJsonResponse(runtimeFixtures.activeLicense);
      }
      if (path === "/api/settings/health") {
        return okJsonResponse(runtimeFixtures.health);
      }
      if (path === "/api/settings/config") {
        return okJsonResponse(runtimeFixtures.initializedConfig);
      }
      if (path === "/api/settings/diagnostics") {
        return okJsonResponse(runtimeFixtures.initializedDiagnostics);
      }
      if (path === "/api/dashboard/context") {
        return okJsonResponse(projectContext);
      }
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [
            {
              id: "project-001",
              name: "Summer Launch",
              description: "Creator flow",
              status: "active",
              currentScriptVersion: 2,
              currentStoryboardVersion: 0,
              createdAt: "2026-04-25T07:00:00Z",
              updatedAt: "2026-04-25T07:45:00Z",
              lastAccessedAt: "2026-04-25T07:45:00Z"
            }
          ],
          currentProject: projectContext
        });
      }
      if (path === "/api/scripts/projects/project-001/document" && method === "GET") {
        return okJsonResponse(cloneValue(scriptDocument));
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = await mountApp("/scripts/topics");
    await flushPromises();

    await vi.waitFor(() => {
      expect(wrapper.findAll(".outline-item")).toHaveLength(3);
      expect(wrapper.find(".outline-list").text()).not.toContain("---");
      expect(wrapper.find(".outline-list").text()).not.toContain("markdown");
      expect(wrapper.find(".script-markdown-preview table").exists()).toBe(true);
      expect(wrapper.get("[data-script-preview]").text()).toContain("改写后脚本主题：工位“续命”杯");
      expect(wrapper.get("[data-script-preview]").text()).toContain("分镜脚本");
      expect(wrapper.get("[data-script-preview]").text()).toContain("工位开场");
      expect(wrapper.get("[data-script-preview]").text()).not.toContain("```");
      expect(wrapper.get("[data-script-preview]").text()).not.toContain("markdown");
    });
  });
});
