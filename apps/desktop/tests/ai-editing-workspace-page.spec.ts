import { flushPromises, mount } from "@vue/test-utils";
import { confirm } from "@tauri-apps/plugin-dialog";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import App from "../src/App.vue";
import { createAppRouter } from "../src/app/router";
import WorkspaceAssetRail from "../src/modules/workspace/WorkspaceAssetRail.vue";
import WorkspaceTimeline from "../src/modules/workspace/WorkspaceTimeline.vue";
import { useTaskBusStore } from "../src/stores/task-bus";

vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn()
}));

describe("M05 AI 剪辑工作台页面", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    vi.mocked(confirm).mockResolvedValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("通过 /workspace/editing 加载真实时间线空态并创建草稿", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    let timelineState: ReturnType<typeof workspaceTimeline> | null = null;

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            message: "当前项目还没有时间线草稿。"
          });
        }
        if (path === "/api/assets" && method === "GET") {
          return okJsonResponse([workspaceAsset()]);
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
          timelineState = workspaceTimeline();
          return okJsonResponse(
            {
              timeline: timelineState,
              message: "已创建时间线草稿。"
            },
            201
          );
        }
        if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
          timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "assembly",
              message: "已保存 M05 剪辑工作台受管轨道。"
            },
            assemblyState: {
              status: "ready",
              sources: [
                sourceState("script"),
                sourceState("storyboard"),
                sourceState("voice"),
                sourceState("subtitle")
              ],
              issues: []
            },
            message: "剪辑工作台时间线已从脚本、分镜、配音和字幕汇入。"
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线本地预检通过。",
            issues: []
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/clips/insert-asset" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            assetId: "asset-warm-room-lamp",
            startMs: 0
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([
              managedClip(
                "asset-clip-warm-room-lamp",
                "managed-video-storyboard",
                "asset",
                "warm-room-lamp-vertical.mp4",
                { sourceId: "asset-warm-room-lamp" }
              ),
              managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面")
            ]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_insert_asset",
              message: "已确认保存资产入轨结果。"
            },
            message: "资产已加入时间线。"
          });
        }
        if (path === "/api/workspace/clips/managed-video-storyboard-01/replace" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            assetId: "asset-warm-room-lamp"
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([
              managedClip(
                "managed-video-storyboard-01",
                "managed-video-storyboard",
                "asset",
                "warm-room-lamp-vertical.mp4",
                { sourceId: "asset-warm-room-lamp" }
              )
            ]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_replace",
              message: "已确认保存资产替换结果。"
            },
            message: "片段已替换。"
          });
        }
        if (path === "/api/workspace/clips/managed-video-storyboard-01/move" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            targetTrackId: "managed-video-storyboard",
            startMs: 500
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([managedClip(
              "managed-video-storyboard-01",
              "managed-video-storyboard",
              "storyboard",
              "S01 · 分镜画面",
              { startMs: 500 }
            )]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_move",
              message: "已确认保存片段位置变更。"
            },
            message: "片段已移动。"
          });
        }
        if (path === "/api/workspace/clips/managed-video-storyboard-01/trim" && method === "POST") {
          expect(JSON.parse(String(init?.body))).toEqual({
            startMs: 1000,
            durationMs: 4500,
            inPointMs: 500
          });
          timelineState = workspaceTimeline([
            managedVideoTrack([managedClip(
              "managed-video-storyboard-01",
              "managed-video-storyboard",
              "storyboard",
              "S01 · 分镜画面",
              { startMs: 1000, durationMs: 4500, inPointMs: 500 }
            )]),
            managedAudioTrack(),
            managedSubtitleTrack()
          ]);
          return okJsonResponse({
            timeline: timelineState,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "clip_trim",
              message: "已确认保存片段裁剪结果。"
            },
            message: "片段已裁剪。"
          });
        }
        if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
          return okJsonResponse({
            status: "blocked",
            task: null,
            message: "AI 剪辑命令尚未接入 Provider，本阶段仅保留时间线草稿。"
          });
        }
        if (path === "/api/tasks/task-workspace-1/cancel" && method === "POST") {
          return okJsonResponse({
            task_id: "task-workspace-1",
            status: "cancelled",
            message: "智能粗剪任务已取消。"
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router, pinia } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/workspace/editing");
    expect(wrapper.find(".editing-workspace-page").exists()).toBe(true);
    expect(wrapper.find(".page-container").exists()).toBe(false);
    expect(calls.some((call) => call.path === "/api/workspace/projects/project-1/timeline")).toBe(
      true
    );
    expect(wrapper.text()).toContain("素材池");
    expect(wrapper.text()).toContain("预览与校验");
    expect(wrapper.text()).not.toContain("播放器");
    expect(wrapper.text()).toContain("基础属性");
    expect(wrapper.text()).toContain("时间线");
    expect(wrapper.text()).toContain("当前项目还没有时间线草稿");
    expect(wrapper.text()).not.toContain("BGM_");

    await wrapper.get('[data-testid="workspace-create-draft-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("主画面");
    expect(wrapper.text()).toContain("基础工具");
    expect(wrapper.text()).toContain("基础属性");
    expect(wrapper.text()).toContain("片段信息");
    expect(wrapper.text()).toContain("时间参数");
    expect(wrapper.text()).toContain("素材来源");
    expect(wrapper.text()).toContain("AI 粗剪建议");
    expect(wrapper.text()).toContain("默认折叠");
    const aiSuggestionDetails = wrapper.get('[data-testid="workspace-ai-suggestion-details"]');
    expect((aiSuggestionDetails.element as HTMLDetailsElement).open).toBe(false);
    const timelineToolbar = wrapper.get('[data-testid="workspace-timeline-toolbar"]');
    expect(timelineToolbar.text()).toContain("选择");
    expect(timelineToolbar.text()).toContain("左移");
    expect(timelineToolbar.text()).toContain("右移");
    expect(timelineToolbar.text()).toContain("左裁");
    expect(timelineToolbar.text()).toContain("右裁");
    expect(timelineToolbar.text()).toContain("分割");
    expect(timelineToolbar.text()).toContain("删除");
    expect(timelineToolbar.text()).toContain("磁吸");
    expect(wrapper.get('[data-testid="workspace-tool-split"]').text()).toContain("分割");
    expect(wrapper.get('[data-testid="workspace-tool-select"]').classes()).toContain(
      "workspace-timeline-toolbar__button--active"
    );
    expect(wrapper.get('[data-testid="workspace-timeline-zoom-value"]').text()).toBe("100%");
    expect(wrapper.findComponent(WorkspaceTimeline).props("zoomPercent")).toBe(100);

    await wrapper.get('[data-testid="workspace-timeline-zoom-in"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-timeline-zoom-value"]').text()).toBe("150%");
    expect(wrapper.findComponent(WorkspaceTimeline).props("zoomPercent")).toBe(150);

    await wrapper.get(".workspace-clip").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("该片段来自资产中心素材，可在后续功能中替换或在资产中心处理。");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline",
      method: "POST",
      body: { name: "主时间线" }
    });

    await wrapper.get('[data-testid="workspace-assemble-button"]').trigger("click");
    await flushPromises();

    const previewCanvas = wrapper.get('[data-testid="workspace-preview-canvas"]');
    expect(previewCanvas.attributes("data-ratio")).toBe("9:16");
    expect(previewCanvas.text()).toContain("9:16");
    expect(wrapper.text()).toContain("分镜预览");
    expect(wrapper.text()).toContain("先按分镜和字幕检查节奏");
    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).toContain("00:");
    expect(wrapper.text()).toContain("分镜占位");
    expect(wrapper.text()).toContain("待处理");
    expect(wrapper.text()).not.toContain("pending");
    expect(wrapper.text()).not.toContain("draft");
    expect(wrapper.text()).not.toContain("延续字幕");
    expect(wrapper.text()).toContain("分镜视频轨");
    expect(wrapper.text()).toContain("配音轨");
    expect(wrapper.text()).toContain("字幕轨");
    expect(wrapper.text()).toContain("资产");
    expect(wrapper.text()).toContain("warm-room-lamp-vertical.mp4");
    expect(wrapper.text()).toContain("加入时间线");
    expect(wrapper.text()).toContain("替换片段");
    expect(wrapper.text()).toContain("受管轨道");
    expect(wrapper.text()).toContain("本地预检");
    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline/assemble",
      method: "POST",
      body: { mode: "merge_managed", timelineName: "主时间线" }
    });

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-clip", {
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard"
    });
    await flushPromises();

    expect((wrapper.get('[data-testid="workspace-tool-move-left"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-move-right"]').element as HTMLButtonElement).disabled).toBe(false);
    expect((wrapper.get('[data-testid="workspace-tool-split"]').element as HTMLButtonElement).disabled).toBe(true);
    expect(wrapper.get('[data-testid="workspace-timeline-toolbar"]').text()).toContain("播放头需要位于选中片段内部");

    const precheckCallsBeforeInsert = calls.filter(
      (call) => call.path === "/api/workspace/timelines/timeline-1/precheck"
    ).length;
    wrapper.findComponent(WorkspaceAssetRail).vm.$emit("asset-insert", "asset-warm-room-lamp");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/timelines/timeline-1/clips/insert-asset",
      method: "POST",
      body: { assetId: "asset-warm-room-lamp", startMs: 0 }
    });
    expect(
      calls.filter((call) => call.path === "/api/workspace/timelines/timeline-1/precheck").length
    ).toBeGreaterThan(precheckCallsBeforeInsert);
    expect(wrapper.text()).toContain("已确认保存资产入轨结果");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-clip", {
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard"
    });
    await flushPromises();

    const precheckCallsBeforeReplace = calls.filter(
      (call) => call.path === "/api/workspace/timelines/timeline-1/precheck"
    ).length;
    wrapper.findComponent(WorkspaceAssetRail).vm.$emit("asset-replace", "asset-warm-room-lamp");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/replace",
      method: "POST",
      body: { assetId: "asset-warm-room-lamp" }
    });
    expect(
      calls.filter((call) => call.path === "/api/workspace/timelines/timeline-1/precheck").length
    ).toBeGreaterThan(precheckCallsBeforeReplace);
    expect(wrapper.text()).toContain("已确认保存资产替换结果");

    await wrapper.get('[data-testid="workspace-precheck-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("时间线本地预检通过");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-commit", {
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 500,
      durationMs: 5000
    });
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/move",
      method: "POST",
      body: { targetTrackId: "managed-video-storyboard", startMs: 500 }
    });
    expect(wrapper.text()).toContain("已确认保存片段位置变更");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("trim-commit", {
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "left",
      startMs: 1000,
      durationMs: 4500,
      inPointMs: 500
    });
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/trim",
      method: "POST",
      body: { startMs: 1000, durationMs: 4500, inPointMs: 500 }
    });
    expect(wrapper.text()).toContain("已确认保存片段裁剪结果");

    const taskBusStore = useTaskBusStore(pinia);
    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.started",
      taskId: "task-workspace-1",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "running",
      progress: 25,
      message: "AI 命令 magic_cut 已进入任务队列。"
    }));
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪处理中");
    expect(wrapper.text()).toContain("AI 命令 magic_cut 已进入任务队列");
    expect(
      (wrapper.get('[data-testid="workspace-magic-cut-button"]').element as HTMLButtonElement)
        .disabled
    ).toBe(true);

    await wrapper.get('[data-testid="workspace-command-cancel-button"]').trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/tasks/task-workspace-1/cancel",
      method: "POST",
      body: undefined
    });
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪已取消");

    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.completed",
      taskId: "task-workspace-1",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "succeeded",
      progress: 100,
      message: "AI 命令 magic_cut 已完成。"
    }));
    await flushPromises();

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("AI 剪辑命令尚未接入 Provider");
  });

  it("AI 受管轨道不等长时提供同步恢复入口并复用汇入接口", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    let timelineState = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面", {
          durationMs: 5000
        })
      ]),
      {
        ...managedAudioTrack(),
        clips: [
          managedClip("managed-audio-voice-01", "managed-audio-voice", "voice_track", "S01 · 配音", {
            durationMs: 3000
          })
        ]
      },
      managedSubtitleTrack()
    ]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/settings/ai-capabilities") return okJsonResponse(aiCapabilitySettings());
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(aiCapabilitySupportMatrix());
        }
        if (path === "/api/settings/ai-providers/catalog") return okJsonResponse(aiProviderCatalog());
        if (path.startsWith("/api/settings/ai-providers/") && path.endsWith("/models")) {
          const pathSegments = path.split("/");
          return okJsonResponse(aiModelCatalog(pathSegments[pathSegments.length - 2] ?? "deepseek"));
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "load",
              message: "已读取时间线草稿。"
            },
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/preview" && method === "GET") {
          return okJsonResponse(timelinePreview());
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([]);
        if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
          timelineState = workspaceTimeline([
            managedVideoTrack([
              managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面", {
                durationMs: 12000
              })
            ]),
            {
              ...managedAudioTrack(),
              clips: [
                managedClip("managed-audio-voice-01", "managed-audio-voice", "voice_track", "S01 · 配音", {
                  durationMs: 12000
                })
              ]
            },
            {
              ...managedSubtitleTrack(),
              clips: [
                managedClip("managed-subtitle-01", "managed-subtitle-track", "subtitle_track", "S01 · 字幕", {
                  durationMs: 12000
                })
              ]
            }
          ]);
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "assembly",
              message: "已保存 M05 剪辑工作台受管轨道。"
            },
            assemblyState: {
              status: "ready",
              sources: [
                sourceState("script"),
                sourceState("storyboard"),
                sourceState("voice"),
                sourceState("subtitle")
              ],
              issues: []
            },
            message: "剪辑工作台时间线已从脚本、分镜、配音和字幕汇入。"
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-sync-recovery"]').text()).toContain("AI 三轨未对齐");
    expect(wrapper.get('[data-testid="workspace-sync-recovery"]').text()).toContain("3 条 AI 受管轨道未对齐到 00:12");

    await wrapper.get('[data-testid="workspace-sync-managed-tracks-button"]').trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline/assemble",
      method: "POST",
      body: { mode: "merge_managed", timelineName: "主时间线" }
    });
    expect(wrapper.find('[data-testid="workspace-sync-recovery"]').exists()).toBe(false);
  });

  it("资产栏请求打开资产中心时使用既有资产中心路由", async () => {
    const { wrapper, router } = await mountEditingWorkspaceWithTimeline();

    const routerPush = vi.spyOn(router, "push");
    wrapper.findComponent(WorkspaceAssetRail).vm.$emit("open-asset-library");
    expect(routerPush).toHaveBeenCalledWith({
      path: "/assets/library",
      query: { from: "workspace" }
    });
    await routerPush.mock.results[0]?.value;

    expect(router.currentRoute.value.path).toBe("/assets/library");
  });

  it("缺少创作来源且时间线为 0 轨时展示恢复路径并可重新同步", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const timelineState = workspaceTimeline([]);
    const warningAssemblyState = {
      status: "warning",
      sources: [
        {
          kind: "script",
          status: "missing",
          label: "脚本文案",
          revision: null,
          trackId: null,
          segmentCount: 0,
          message: "缺少脚本文案，请先完成脚本。"
        },
        {
          kind: "storyboard",
          status: "missing",
          label: "分镜规划",
          revision: null,
          trackId: null,
          segmentCount: 0,
          message: "缺少分镜规划，请先完成分镜。"
        },
        {
          kind: "voice",
          status: "missing",
          label: "配音轨",
          revision: null,
          trackId: null,
          segmentCount: 0,
          message: "缺少配音轨，请先完成配音。"
        },
        {
          kind: "subtitle",
          status: "missing",
          label: "字幕轨",
          revision: null,
          trackId: null,
          segmentCount: 0,
          message: "缺少字幕轨，请先完成字幕。"
        }
      ],
      issues: [
        "缺少脚本文案、分镜规划、配音轨和字幕轨，无法生成完整 AI 三轨。"
      ]
    };

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "load",
              message: "已读取时间线草稿，但创作来源未补齐。"
            },
            assemblyState: warningAssemblyState,
            message: "创作来源未补齐，当前时间线没有可汇入轨道。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([]);
        if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "assembly",
              message: "已重新检查创作来源，仍缺少生成 AI 三轨所需内容。"
            },
            assemblyState: warningAssemblyState,
            message: "缺少创作来源，暂不能生成完整 AI 三轨。"
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    const recovery = wrapper.get('[data-testid="workspace-source-recovery"]');
    expect(recovery.text()).toContain("缺少创作来源");
    expect(recovery.text()).toContain("无法生成完整 AI 三轨");
    expect(recovery.text()).toContain("脚本文案");
    expect(recovery.text()).toContain("分镜规划");
    expect(recovery.text()).toContain("配音轨");
    expect(recovery.text()).toContain("字幕轨");
    expect(recovery.text()).toContain("当前时间线显示 0 轨");
    expect(recovery.text()).toContain("先完成脚本、分镜、配音和字幕");

    await wrapper.get('[data-testid="workspace-source-recovery-assemble-button"]').trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/timeline/assemble",
      method: "POST",
      body: { mode: "merge_managed", timelineName: "主时间线" }
    });
  });

  it("缺少配音轨时提供配音中心、AI 设置、预检和重新同步恢复动作", async () => {
    const timelineState = workspaceTimeline([managedVideoTrack(), managedSubtitleTrack()]);
    const warningAssemblyState = {
      status: "warning",
      sources: [
        sourceState("script"),
        sourceState("storyboard"),
        {
          kind: "voice",
          status: "missing",
          label: "配音轨",
          revision: null,
          trackId: null,
          segmentCount: 0,
          message: "当前未配置可用 TTS Provider，已保留配音轨草稿。"
        },
        sourceState("subtitle")
      ],
      issues: ["缺少可用配音轨。当前未配置 TTS Provider，请先完成配音或打开 AI 设置。"]
    };

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "load",
              message: "已读取时间线草稿，配音轨未就绪。"
            },
            assemblyState: warningAssemblyState,
            message: "缺少配音轨，暂不能生成完整 AI 三轨。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([]);
        if (path === "/api/workspace/timelines/timeline-1/preview" && method === "GET") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线结构预览已生成。",
            previewUrl: null,
            previewMode: "manifest",
            media: null,
            error: null
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "warning",
            message: "当前未配置 TTS Provider，配音轨不可用。",
            issues: ["当前未配置 TTS Provider，请先在 AI 与系统设置中配置配音能力。"]
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    const recovery = wrapper.get('[data-testid="workspace-source-recovery"]');
    expect(recovery.text()).toContain("缺少配音轨");
    expect(recovery.text()).toContain("当前未配置 TTS Provider");
    expect(wrapper.get('[data-testid="workspace-source-recovery-voice-button"]').text()).toContain("去配音中心");
    expect(wrapper.get('[data-testid="workspace-source-recovery-settings-button"]').text()).toContain("打开 AI 设置");
    expect(wrapper.get('[data-testid="workspace-source-recovery-precheck-button"]').text()).toContain("本地预检");
    expect(wrapper.get('[data-testid="workspace-source-recovery-assemble-button"]').text()).toContain("重新同步 AI 三轨");

    const routerPush = vi.spyOn(router, "push");
    await wrapper.get('[data-testid="workspace-source-recovery-voice-button"]').trigger("click");
    await routerPush.mock.results[0]?.value;
    expect(routerPush).toHaveBeenCalledWith({
      path: "/voice/studio",
      query: { from: "workspace", missing: "voice" }
    });

    await router.push("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-source-recovery-settings-button"]').trigger("click");
    await routerPush.mock.results[1]?.value;
    expect(routerPush).toHaveBeenCalledWith({
      path: "/settings/ai-system",
      query: {
        section: "capability",
        capability: "tts",
        from: "workspace"
      }
    });

    await wrapper.get('[data-testid="workspace-source-recovery-precheck-button"]').trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("当前未配置 TTS Provider，配音轨不可用。");
  });

  it("时间线移动预览时展示正在调整位置反馈", async () => {
    const { wrapper } = await mountEditingWorkspaceWithTimeline();

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-preview", {
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 1500,
      durationMs: 5000
    });
    await flushPromises();

    const feedback = wrapper.get('[data-testid="workspace-timeline-drag-feedback"]');
    expect(feedback.text()).toContain("正在调整位置");
    expect(feedback.text()).toContain("目标起点：00:01");
    expect(feedback.text()).toContain("时长：00:05");
  });

  it("时间线裁剪预览时展示起点结束和时长反馈", async () => {
    const { wrapper } = await mountEditingWorkspaceWithTimeline();

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("trim-preview", {
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "right",
      startMs: 1000,
      durationMs: 4500,
      inPointMs: 500
    });
    await flushPromises();

    const feedback = wrapper.get('[data-testid="workspace-timeline-drag-feedback"]');
    expect(feedback.text()).toContain("正在裁剪片段");
    expect(feedback.text()).toContain("起点：00:01");
    expect(feedback.text()).toContain("结束：00:05");
    expect(feedback.text()).toContain("时长：00:04");
  });

  it("时间线拖拽取消后隐藏临时反馈", async () => {
    const { wrapper } = await mountEditingWorkspaceWithTimeline();

    const preview = {
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 1500,
      durationMs: 5000
    };
    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-preview", preview);
    await flushPromises();
    expect(wrapper.find('[data-testid="workspace-timeline-drag-feedback"]').exists()).toBe(true);

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("drag-cancel", preview);
    await flushPromises();

    expect(wrapper.find('[data-testid="workspace-timeline-drag-feedback"]').exists()).toBe(false);
  });

  it("时间线移动提交后隐藏临时反馈并继续执行预检", async () => {
    const { calls, wrapper } = await mountEditingWorkspaceWithTimeline();

    const preview = {
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 1500,
      durationMs: 5000
    };
    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-preview", preview);
    await flushPromises();
    expect(wrapper.find('[data-testid="workspace-timeline-drag-feedback"]').exists()).toBe(true);

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("move-commit", preview);
    await flushPromises();

    expect(wrapper.find('[data-testid="workspace-timeline-drag-feedback"]').exists()).toBe(false);
    expect(calls).toContainEqual({
      path: "/api/workspace/clips/managed-video-storyboard-01/move",
      method: "POST",
      body: { targetTrackId: "managed-video-storyboard", startMs: 1500 }
    });
    expect(calls.some((call) => call.path === "/api/workspace/timelines/timeline-1/precheck")).toBe(true);
  });

  it("按钮聚焦时空格键保留按钮语义而不触发全局播放快捷键", async () => {
    const { wrapper } = await mountEditingWorkspaceWithTimeline();
    const saveButton = wrapper.get('[data-testid="workspace-save-button"]');

    (saveButton.element as HTMLButtonElement).focus();
    saveButton.element.dispatchEvent(new KeyboardEvent("keydown", {
      bubbles: true,
      cancelable: true,
      key: " "
    }));
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).toContain("播放");
    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).not.toContain("暂停");
  });

  it("智能粗剪提交后立即用顶部提示展示 Runtime 入队反馈", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "load",
              message: "已读取时间线草稿。"
            },
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线本地预检通过。",
            issues: []
          });
        }
        if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
          return okJsonResponse({
            status: "queued",
            task: {
              id: "task-workspace-queued",
              kind: "ai-workspace-command",
              task_type: "ai-workspace-command",
              taskType: "ai-workspace-command",
              project_id: "project-1",
              projectId: "project-1",
              status: "queued",
              progress: 0,
              message: "AI 命令 magic_cut 已进入任务队列。"
            },
            message: "AI 命令已进入任务队列，正在通过 TaskBus 处理。"
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-precheck-button"]').trigger("click");
    await flushPromises();
    expect(wrapper.find(".dashboard-alert").text()).toContain("时间线本地预检通过");

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({
      path: "/api/workspace/projects/project-1/ai-commands",
      method: "POST",
      body: {
        timelineId: "timeline-1",
        capabilityId: "magic_cut",
        parameters: {
          selectedTrackId: "managed-video-storyboard",
          selectedClipId: null
        }
      }
    });
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain(
      "AI 命令 magic_cut 已进入任务队列"
    );
  });

  it("智能粗剪能力停用时禁用按钮并阻止 Runtime 命令提交", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/settings/ai-capabilities") {
          return okJsonResponse(aiCapabilitySettings({ magicCutEnabled: false }));
        }
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(aiCapabilitySupportMatrix());
        }
        if (path === "/api/settings/ai-providers/catalog") {
          return okJsonResponse(aiProviderCatalog());
        }
        if (path.startsWith("/api/settings/ai-providers/") && path.endsWith("/models")) {
          const pathSegments = path.split("/");
          return okJsonResponse(aiModelCatalog(pathSegments[pathSegments.length - 2] ?? "deepseek"));
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: true,
              updatedAt: now(),
              source: "load",
              message: "已读取时间线草稿。"
            },
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线本地预检通过。",
            issues: []
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    const magicCutButton = wrapper.get('[data-testid="workspace-magic-cut-button"]');
    expect((magicCutButton.element as HTMLButtonElement).disabled).toBe(true);
    expect(wrapper.text()).toContain("智能粗剪暂不可用");
    expect(wrapper.text()).toContain("智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。");
    expect(calls.some((call) => call.path === "/api/workspace/projects/project-1/ai-commands")).toBe(false);

    const initialCapabilityLoadCount = calls.filter((call) => call.path === "/api/settings/ai-capabilities").length;
    await wrapper.get('[data-testid="workspace-ai-refresh-button"]').trigger("click");
    await flushPromises();
    expect(calls.filter((call) => call.path === "/api/settings/ai-capabilities").length).toBe(
      initialCapabilityLoadCount + 1
    );

    const routerPush = vi.spyOn(router, "push");
    await wrapper.get('[data-testid="workspace-ai-settings-button"]').trigger("click");
    await flushPromises();
    expect(routerPush).toHaveBeenCalledWith({
      path: "/settings/ai-system",
      query: {
        section: "capability",
        capability: "magic_cut",
        from: "workspace"
      }
    });
  });

  it("未保存时间线时打开 AI 设置必须经过离开确认", async () => {
    const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/settings/ai-capabilities") {
          return okJsonResponse(aiCapabilitySettings({ magicCutEnabled: false }));
        }
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(aiCapabilitySupportMatrix());
        }
        if (path === "/api/settings/ai-providers/catalog") {
          return okJsonResponse(aiProviderCatalog());
        }
        if (path.startsWith("/api/settings/ai-providers/") && path.endsWith("/models")) {
          const pathSegments = path.split("/");
          return okJsonResponse(aiModelCatalog(pathSegments[pathSegments.length - 2] ?? "deepseek"));
        }
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: {
              saved: false,
              updatedAt: now(),
              source: "clip_move",
              message: "时间线有未保存的更改。"
            },
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "ready",
            message: "时间线本地预检通过。",
            issues: []
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    vi.mocked(confirm).mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    const routerPush = vi.spyOn(router, "push");
    await wrapper.get('[data-testid="workspace-ai-settings-button"]').trigger("click");
    await routerPush.mock.results[0]?.value;
    expect(confirm).toHaveBeenCalledWith("时间线有未保存的更改，确定要离开吗？", {
      title: "离开 AI 剪辑工作台",
      kind: "warning"
    });
    expect(router.currentRoute.value.path).toBe("/workspace/editing");

    await wrapper.get('[data-testid="workspace-ai-settings-button"]').trigger("click");
    await routerPush.mock.results[1]?.value;
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(router.currentRoute.value.path).toBe("/settings/ai-system");
    expect(router.currentRoute.value.query).toMatchObject({
      section: "capability",
      capability: "magic_cut",
      from: "workspace"
    });
    await flushPromises();
  });

  it("Runtime 返回 AI 能力停用时展示可恢复提示且不显示已入队", async () => {
    const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: null,
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
          return errorJsonResponse(400, "当前 AI 能力已停用。");
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, router } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.find(".dashboard-alert").text()).toContain(
      "智能粗剪暂不可用：当前 AI 能力已停用。"
    );
    expect(wrapper.get('[data-testid="workspace-ai-settings-button"]').text()).toContain("打开 AI 设置");
    expect(wrapper.get('[data-testid="workspace-ai-refresh-button"]').text()).toContain("重新同步 AI 状态");
    expect(wrapper.text()).not.toContain("AI 命令 magic_cut 已进入任务队列");

    const routerPush = vi.spyOn(router, "push");
    await wrapper.get('[data-testid="workspace-ai-settings-button"]').trigger("click");
    await flushPromises();
    expect(routerPush).toHaveBeenCalledWith({
      path: "/settings/ai-system",
      query: {
        section: "capability",
        capability: "magic_cut",
        from: "workspace"
      }
    });
  });

  it("重新同步 AI 状态成功后清理智能粗剪旧阻断提示", async () => {
    const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);
    const calls: Array<{ method: string; path: string }> = [];

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            activeTask: null,
            saveState: null,
            message: "剪辑工作台已加载。"
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/settings/ai-capabilities") return okJsonResponse(aiCapabilitySettings());
        if (path === "/api/settings/ai-capabilities/support-matrix") {
          return okJsonResponse(aiCapabilitySupportMatrix());
        }
        if (path === "/api/settings/ai-providers/catalog") return okJsonResponse(aiProviderCatalog());
        if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
          return errorJsonResponse(400, "当前 AI 能力已停用。");
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-magic-cut-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("智能粗剪暂不可用：当前 AI 能力已停用。");
    const capabilityLoadsBeforeRefresh = calls.filter(
      (call) => call.path === "/api/settings/ai-capabilities"
    ).length;

    await wrapper.get('[data-testid="workspace-ai-refresh-button"]').trigger("click");
    await flushPromises();

    expect(calls.filter((call) => call.path === "/api/settings/ai-capabilities").length)
      .toBeGreaterThan(capabilityLoadsBeforeRefresh);
    expect(wrapper.text()).not.toContain("智能粗剪暂不可用：当前 AI 能力已停用。");
  });

  it("从 TaskBus 恢复的智能粗剪终态会保留反馈并在成功后读取建议", async () => {
    const { calls, pinia, wrapper } = await mountEditingWorkspaceWithTimeline();
    const taskBusStore = useTaskBusStore(pinia);

    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.started",
      taskId: "task-recovered-failed",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "running",
      progress: 36,
      message: "正在恢复智能粗剪任务。"
    }));
    await flushPromises();
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪处理中");

    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.failed",
      taskId: "task-recovered-failed",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "failed",
      progress: 63,
      message: "Provider 响应超时，请稍后重试。"
    }));
    await flushPromises();
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪失败");
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("Provider 响应超时，请稍后重试。");

    const suggestionLoadCountBeforeSuccess = calls.filter(
      (call) => call.path === "/api/workspace/projects/project-1/magic-cut-suggestions/latest?timelineId=timeline-1" && call.method === "GET"
    ).length;
    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.started",
      taskId: "task-recovered-success",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "running",
      progress: 72,
      message: "正在生成智能粗剪建议。"
    }));
    await flushPromises();
    taskBusStore.handleIncomingMessage(JSON.stringify({
      schema_version: 1,
      type: "task.completed",
      taskId: "task-recovered-success",
      taskType: "ai-workspace-command",
      projectId: "project-1",
      status: "succeeded",
      progress: 100,
      message: "已生成 1 条智能粗剪建议，等待审阅。"
    }));
    await flushPromises();
    await flushPromises();

    expect(
      calls.filter((call) => call.path === "/api/workspace/projects/project-1/magic-cut-suggestions/latest?timelineId=timeline-1" && call.method === "GET").length
    ).toBeGreaterThan(suggestionLoadCountBeforeSuccess);
    expect(
      calls.filter((call) => call.path === "/api/workspace/projects/project-1/timeline" && call.method === "GET").length
    ).toBe(1);
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪建议已生成");
    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("等待审阅");
    expect(wrapper.text()).toContain("AI 粗剪建议 · 1 条待审阅");
  });

  it("联动播放器、属性面板和预检问题定位", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const saveRequest = deferredResponse();
    let timelineState = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面", {
          durationMs: 5000
        }),
        managedClip("managed-video-storyboard-02", "managed-video-storyboard", "storyboard", "S02 · 分镜画面", {
          startMs: 6000,
          durationMs: 4000
        })
      ]),
      managedAudioTrack(),
      managedSubtitleTrack()
    ]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });

        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            message: "已加载时间线草稿。"
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "warning",
            message: "时间线本地预检发现 1 个问题。",
            issues: ["片段 managed-audio-voice-01 音频峰值缺少复核。"]
          });
        }
        if (path === "/api/workspace/timelines/timeline-1" && method === "PATCH") {
          return saveRequest.promise;
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-asset-tab-storyboard"]').trigger("click");
    await flushPromises();

    const sourceCards = wrapper.findAll(".workspace-asset-rail__item-card");
    expect(sourceCards).toHaveLength(2);
    await sourceCards[1].trigger("click");
    await flushPromises();

    expect(wrapper.findAll(".workspace-asset-rail__item--active")).toHaveLength(1);
    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("S02 · 分镜画面");
    expect(wrapper.get('[data-testid="workspace-preview-transport"]').text()).toContain("00:06");
    expect(wrapper.text()).toContain("当前片段：S02 · 分镜画面");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-track", "managed-video-storyboard");
    wrapper.findComponent(WorkspaceTimeline).vm.$emit("playhead", 6500);
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("S02 · 分镜画面");
    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("当前时间：00:06");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-clip", {
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard"
    });
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("画面来源：分镜占位");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-clip", {
      clipId: "managed-audio-voice-01",
      trackId: "managed-audio-voice"
    });
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("音频状态：配音片段");
    expect(wrapper.text()).toContain("当前片段：S01 · 配音");

    wrapper.findComponent(WorkspaceTimeline).vm.$emit("select-clip", {
      clipId: "managed-subtitle-01",
      trackId: "managed-subtitle-track"
    });
    await flushPromises();

    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("字幕文本：This lamp made me cancel my dinner plan.");

    await wrapper.get('[data-testid="workspace-precheck-button"]').trigger("click");
    await flushPromises();

    const issueButton = wrapper.get('[data-testid="workspace-precheck-issue"]');
    expect(issueButton.text()).toContain("片段 managed-audio-voice-01");
    await issueButton.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("当前片段：S01 · 配音");
    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("音频状态：配音片段");

    await wrapper.get('[data-testid="workspace-save-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("保存中");
    expect(wrapper.text()).toContain("正在将当前时间线草稿写回 Runtime。");

    saveRequest.resolve(
      okJsonResponse({
        timeline: timelineState,
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "manual_save",
          message: "已保存当前时间线。"
        },
        message: "时间线已保存。"
      })
    );
    await flushPromises();

    expect(wrapper.text()).toContain("已保存当前时间线。");
    expect(calls).toContainEqual({
      path: "/api/workspace/timelines/timeline-1",
      method: "PATCH",
      body: {
        name: "主时间线",
        durationSeconds: 12,
        tracks: timelineState.tracks
      }
    });
  });

  it("优先展示结构化预检问题并从问题按钮精准定位片段", async () => {
    const timelineState = workspaceTimeline([
      managedVideoTrack([
        managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面")
      ]),
      managedAudioTrack()
    ]);

    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status") return okJsonResponse(activeLicense());
        if (path === "/api/settings/health") return okJsonResponse(health());
        if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
        if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
        if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
        if (path === "/api/dashboard/summary") {
          return okJsonResponse({
            recentProjects: [],
            currentProject: {
              projectId: "project-1",
              projectName: "短视频剪辑项目",
              status: "active"
            }
          });
        }
        if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
        if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
          return okJsonResponse({
            timeline: timelineState,
            message: "已加载时间线草稿。"
          });
        }
        if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
          return okJsonResponse({
            timelineId: "timeline-1",
            status: "warning",
            message: "时间线本地预检发现 1 个问题。",
            issues: ["旧版字符串问题不应优先展示。"],
            issueDetails: [
              {
                id: "issue-audio-peak",
                message: "配音峰值缺少复核。",
                suggestion: "打开配音轨重新检查峰值。",
                targetType: "clip",
                targetLabel: "S01 · 配音",
                clipId: "managed-audio-voice-01",
                trackId: "managed-audio-voice",
                actionLabel: "定位片段"
              }
            ]
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/workspace/editing");
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-testid="workspace-precheck-button"]').trigger("click");
    await flushPromises();

    const issueButton = wrapper.get('[data-testid="workspace-precheck-issue"]');
    expect(wrapper.text()).toContain("配音峰值缺少复核。");
    expect(wrapper.text()).toContain("打开配音轨重新检查峰值。");
    expect(wrapper.text()).toContain("片段：S01 · 配音");
    expect(wrapper.text()).not.toContain("旧版字符串问题不应优先展示。");
    expect(issueButton.text()).toContain("定位片段");

    await issueButton.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("当前片段：S01 · 配音");
    expect(wrapper.get('[data-testid="workspace-preview-canvas"]').text()).toContain("音频状态：配音片段");
  });
});

function createRouteAwareFetch(
  resolver: (path: string, method: string, init?: RequestInit) => unknown
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const requestUrl = new URL(String(input));
    const path = `${requestUrl.pathname}${requestUrl.search}`;
    const method = (init?.method ?? "GET").toUpperCase();
    try {
      return resolver(path, method, init);
    } catch (error) {
      if (
        method === "GET" &&
        path === "/api/workspace/timelines/timeline-1/preview" &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        return okJsonResponse(timelinePreview());
      }
      if (
        method === "GET" &&
        path === "/api/bootstrap/readiness" &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        return okJsonResponse(bootstrapReadiness());
      }
      if (
        method === "GET" &&
        path === "/api/settings/ai-capabilities" &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        return okJsonResponse(aiCapabilitySettings());
      }
      if (
        method === "GET" &&
        path === "/api/settings/ai-capabilities/support-matrix" &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        return okJsonResponse(aiCapabilitySupportMatrix());
      }
      if (
        method === "GET" &&
        path === "/api/settings/ai-providers/catalog" &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        return okJsonResponse(aiProviderCatalog());
      }
      if (
        method === "GET" &&
        path.startsWith("/api/settings/ai-providers/") &&
        path.endsWith("/models") &&
        error instanceof Error &&
        error.message.startsWith("Unhandled request")
      ) {
        const pathSegments = path.split("/");
        return okJsonResponse(aiModelCatalog(pathSegments[pathSegments.length - 2] ?? "deepseek"));
      }
      throw error;
    }
  });
}

function okJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => ({
      ok: true,
      data
    })
  };
}

function timelinePreview() {
  return {
    timelineId: "timeline-1",
    status: "ready",
    message: "时间线本地预览已生成，包含真实轨道与片段摘要。",
    previewUrl: "data:application/json;charset=utf-8,%7B%22timelineId%22%3A%22timeline-1%22%7D",
    previewMode: "manifest",
    media: null,
    error: null
  };
}

function errorJsonResponse(status: number, error: string) {
  return {
    ok: false,
    status,
    json: async () => ({
      ok: false,
      error,
      requestId: "req-workspace"
    })
  };
}

function deferredResponse() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((promiseResolve) => {
    resolve = promiseResolve;
  });

  return { promise, resolve };
}

async function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(pinia, createMemoryHistory());
  router.push(path);
  await router.isReady();

  const wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper, router, pinia };
}

async function mountEditingWorkspaceWithTimeline() {
  const timelineState = workspaceTimeline([managedVideoTrack(), managedAudioTrack(), managedSubtitleTrack()]);
  const calls: Array<{ body?: unknown; method: string; path: string }> = [];

  vi.stubGlobal(
    "fetch",
    createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });

      if (path === "/api/license/status") return okJsonResponse(activeLicense());
      if (path === "/api/settings/health") return okJsonResponse(health());
      if (path === "/api/settings/config") return okJsonResponse(initializedConfig());
      if (path === "/api/settings/diagnostics") return okJsonResponse(initializedDiagnostics());
      if (path === "/api/ai-providers/health") return okJsonResponse(providerHealth());
      if (path === "/api/dashboard/summary") {
        return okJsonResponse({
          recentProjects: [],
          currentProject: {
            projectId: "project-1",
            projectName: "短视频剪辑项目",
            status: "active"
          }
        });
      }
      if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
        return okJsonResponse({
          timeline: timelineState,
          activeTask: null,
          saveState: null,
          message: "剪辑工作台已加载。"
        });
      }
      if (path === "/api/assets" && method === "GET") return okJsonResponse([workspaceAsset()]);
      if (path === "/api/workspace/clips/managed-video-storyboard-01/move" && method === "POST") {
        return okJsonResponse({
          timeline: timelineState,
          saveState: {
            saved: true,
            updatedAt: now(),
            source: "clip_move",
            message: "已确认保存片段位置变更。"
          },
          message: "片段已移动。"
        });
      }
      if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
        return okJsonResponse({
          timelineId: "timeline-1",
          status: "ready",
          message: "时间线本地预检通过。",
          issues: []
        });
      }
      if (path === "/api/workspace/projects/project-1/magic-cut-suggestions/latest?timelineId=timeline-1" && method === "GET") {
        return okJsonResponse(magicCutSuggestion());
      }

      throw new Error(`Unhandled request: ${method} ${path}`);
    })
  );

  const mounted = await mountApp("/workspace/editing");
  await flushPromises();
  await flushPromises();

  return { ...mounted, calls };
}

function activeLicense() {
  return {
    active: true,
    restrictedMode: false,
    machineCode: "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
    machineBound: true,
    licenseType: "perpetual",
    maskedCode: "TK-O****************0001",
    activatedAt: "2026-04-11T10:00:00Z"
  };
}

function health() {
  return {
    service: "online",
    version: "0.1.1",
    now: "2026-04-11T10:00:00Z",
    mode: "development"
  };
}

function providerHealth() {
  return {
    providers: [
      {
        provider: "openai",
        label: "OpenAI",
        readiness: "ready",
        lastCheckedAt: "2026-04-11T10:00:00Z",
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      }
    ],
    refreshedAt: "2026-04-11T10:00:00Z"
  };
}

function aiCapabilitySettings(options: { magicCutEnabled?: boolean; providerConfigured?: boolean } = {}) {
  const magicCutEnabled = options.magicCutEnabled ?? true;
  const providerConfigured = options.providerConfigured ?? true;

  return {
    scope: "local",
    configVersion: 1,
    diagnosticSummary: providerConfigured ? "AI 能力已配置。" : "Provider 密钥缺失。",
    capabilities: [
      {
        capabilityId: "magic_cut",
        enabled: magicCutEnabled,
        provider: "deepseek",
        model: "deepseek-chat",
        agentRole: "TikTok 智能粗剪 Agent",
        systemPrompt: "输出剪辑操作。",
        userPromptTemplate: "{{timeline_context}}",
        promptPreview: null
      }
    ],
    providers: [
      {
        provider: "deepseek",
        label: "DeepSeek",
        scope: "local",
        configured: providerConfigured,
        maskedSecret: providerConfigured ? "sk-***" : "",
        baseUrl: "https://api.deepseek.com",
        secretSource: providerConfigured ? "secure_store" : "none",
        supportsTextGeneration: true,
        readiness: providerConfigured ? "ready" : "blocked",
        lastCheckedAt: now(),
        errorCode: providerConfigured ? "" : "ai_provider_not_configured",
        errorMessage: providerConfigured ? "" : "Provider API Key 尚未配置。"
      }
    ]
  };
}

function aiCapabilitySupportMatrix(options: { includeMagicCutModel?: boolean } = {}) {
  const includeMagicCutModel = options.includeMagicCutModel ?? true;
  return {
    capabilities: [
      {
        capabilityId: "magic_cut",
        providers: ["deepseek"],
        models: includeMagicCutModel
          ? [
              {
                provider: "deepseek",
                modelId: "deepseek-chat",
                displayName: "DeepSeek Chat",
                capabilityTypes: ["text_generation"]
              }
            ]
          : []
      }
    ]
  };
}

function aiProviderCatalog(options: { configured?: boolean } = {}) {
  const configured = options.configured ?? true;
  return [
    {
      provider: "deepseek",
      label: "DeepSeek",
      kind: "hosted",
      region: "global",
      category: "text",
      protocol: "openai_compatible",
      modelSyncMode: "static",
      tags: ["text"],
      configured,
      baseUrl: "https://api.deepseek.com",
      secretSource: configured ? "secure_store" : "none",
      capabilities: ["text_generation"],
      requiresBaseUrl: false,
      supportsModelDiscovery: false,
      status: configured ? "ready" : "blocked"
    }
  ];
}

function aiModelCatalog(providerId: string) {
  return [
    {
      provider: providerId,
      modelId: providerId === "openai" ? "gpt-5.4" : "deepseek-chat",
      displayName: providerId === "openai" ? "GPT-5.4" : "DeepSeek Chat",
      enabled: true,
      capabilityTypes: ["text_generation"],
      inputModalities: ["text"],
      outputModalities: ["text"],
      contextWindow: 64000,
      defaultFor: providerId === "openai" ? [] : ["magic_cut"]
    }
  ];
}

function initializedConfig() {
  return {
    revision: 2,
    runtime: {
      mode: "development",
      workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
    },
    paths: {
      cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
      exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
      logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "openai",
      model: "gpt-5.4",
      voice: "alloy",
      subtitleMode: "balanced"
    }
  };
}

function initializedDiagnostics() {
  return {
    databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
    logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
    revision: 2,
    mode: "development",
    healthStatus: "online"
  };
}

function bootstrapReadiness() {
  return {
    status: "ready",
    canContinue: true,
    checkedAt: "2026-04-17T10:00:00Z",
    items: [
      {
        key: "license",
        label: "许可证校验",
        status: "ok",
        detail: "许可证已激活。",
        errorCode: null,
        blockedReason: null,
        affectedTarget: "许可证",
        nextStep: null,
        action: null,
        checkedAt: "2026-04-17T10:00:00Z"
      },
      {
        key: "directories",
        label: "目录初始化",
        status: "ok",
        detail: "工作区目录已完成初始化。",
        errorCode: null,
        blockedReason: null,
        affectedTarget: "本地目录",
        nextStep: null,
        action: null,
        checkedAt: "2026-04-17T10:00:00Z"
      }
    ],
    blockers: []
  };
}

function now() {
  return "2026-04-17T10:00:00Z";
}

function workspaceTimeline(tracks = [manualVideoTrack()]) {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function workspaceAsset() {
  return {
    id: "asset-warm-room-lamp",
    name: "warm-room-lamp-vertical.mp4",
    type: "video",
    source: "asset",
    filePath: "G:/assets/warm-room-lamp-vertical.mp4",
    fileSizeBytes: 2048000,
    durationMs: 7200,
    thumbnailPath: null,
    tags: null,
    projectId: "project-1",
    metadataJson: null,
    sourceInfo: {
      source: "import",
      projectId: "project-1",
      groupId: null,
      filePath: "G:/assets/warm-room-lamp-vertical.mp4",
      metadataSummary: {}
    },
    availability: {
      status: "available",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: now(),
    updatedAt: now()
  };
}

function magicCutSuggestion() {
  return {
    id: "suggestion-1",
    projectId: "project-1",
    timelineId: "timeline-1",
    timelineVersionToken: "sha256:timeline-token",
    status: "pending_review",
    summary: "建议压缩开场停顿。",
    operations: [
      {
        id: "operation-trim-1",
        action: "trim",
        clipId: "managed-video-storyboard-01",
        trackId: "managed-video-storyboard",
        targetTrackId: null,
        originalStartMs: 0,
        originalDurationMs: 5000,
        suggestedStartMs: 0,
        suggestedDurationMs: 3000,
        splitAtMs: null,
        reason: "开场停顿过长。",
        risk: null
      }
    ],
    createdAt: now(),
    updatedAt: now(),
    appliedAt: null
  };
}

function manualVideoTrack() {
  return {
    id: "track-video",
    kind: "video",
    name: "主画面",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips: [
      {
        id: "clip-video",
        trackId: "track-video",
        sourceType: "manual",
        sourceId: null,
        label: "开场镜头",
        startMs: 0,
        durationMs: 4200,
        inPointMs: 0,
        outPointMs: null,
        status: "ready",
        metadata: {
          sourceKind: "asset",
          sourceRevision: null,
          segmentIndex: null,
          segmentId: null,
          text: null,
          visualPrompt: null
        }
      }
    ]
  };
}

function managedVideoTrack(clips = [
  managedClip("managed-video-storyboard-01", "managed-video-storyboard", "storyboard", "S01 · 分镜画面")
]) {
  return {
    id: "managed-video-storyboard",
    kind: "video",
    name: "分镜视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function managedAudioTrack() {
  return {
    id: "managed-audio-voice",
    kind: "audio",
    name: "配音轨",
    orderIndex: 1,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-audio-voice-01", "managed-audio-voice", "voice_track", "S01 · 配音")
    ]
  };
}

function managedSubtitleTrack() {
  return {
    id: "managed-subtitle-track",
    kind: "subtitle",
    name: "字幕轨",
    orderIndex: 2,
    locked: false,
    muted: false,
    clips: [
      managedClip("managed-subtitle-01", "managed-subtitle-track", "subtitle_track", "S01 · 字幕")
    ]
  };
}

function managedClip(
  id: string,
  trackId: string,
  sourceType: string,
  label: string,
  overrides: Partial<{
    startMs: number;
    durationMs: number;
    inPointMs: number;
    outPointMs: number | null;
    status: string;
    sourceId: string | null;
    metadata: Record<string, unknown>;
  }> = {}
) {
  const text = "This lamp made me cancel my dinner plan.";

  return {
    id,
    trackId,
    sourceType,
    sourceId: overrides.sourceId ?? `${sourceType}-1`,
    label,
    startMs: 0,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: sourceType === "storyboard" ? "pending" : "ready",
    metadata: {
      sourceKind: sourceType === "storyboard" ? "storyboard" : sourceType,
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: "S01",
      text,
      visualPrompt: "墙灯亮起，房间从冷光转暖光。"
    },
    ...overrides
  };
}

function sourceState(kind: string) {
  return {
    kind,
    status: "ready",
    label: kind,
    revision: kind === "script" || kind === "storyboard" ? 1 : null,
    trackId: kind === "voice" || kind === "subtitle" ? `${kind}-track` : null,
    segmentCount: 1,
    message: "已读取。"
  };
}
