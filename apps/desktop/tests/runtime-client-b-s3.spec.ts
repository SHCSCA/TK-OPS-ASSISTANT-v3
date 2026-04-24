import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  okJsonResponse
} from "./runtime-helpers";

import {
  applyVideoExtractionToProject,
  extractVideoStructure,
  fetchScriptDocument,
  fetchVideoStructure
} from "@/app/runtime-client";

describe("B-S3 Runtime client contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses canonical B-S3 routes and request shapes", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });
        return okJsonResponse(sampleResponse(path, method));
      })
    );

    const runtimeClient = await import("@/app/runtime-client");

    await runtimeClient.generateScriptTitleVariants("project-1", {
      topic: "短视频开场钩子",
      count: 3
    });
    await runtimeClient.listScriptVersions("project-1");
    await runtimeClient.restoreScriptVersion("project-1", "version-2");
    await runtimeClient.rewriteScriptSegment("project-1", "segment-1", {
      instructions: "改得更有冲击力"
    });
    await runtimeClient.listPromptTemplates("script_segment_rewrite");
    await runtimeClient.createPromptTemplate({
      kind: "script_segment_rewrite",
      name: "强钩子",
      description: "用于强化短视频开场钩子",
      content: "请把这一段改得更抓人。"
    });
    await runtimeClient.updatePromptTemplate("template-1", {
      kind: "script_segment_rewrite",
      name: "强钩子 v2",
      description: "用于强化短视频开场钩子",
      content: "请把这一段改得更有冲击力。"
    });
    await runtimeClient.deletePromptTemplate("template-1");
    await runtimeClient.createStoryboardShot("project-1", {
      title: "开场镜头",
      summary: "镜头推进产品",
      visualPrompt: "竖屏，快速推进"
    });
    await runtimeClient.updateStoryboardShot("project-1", "shot-1", {
      title: "开场特写"
    });
    await runtimeClient.deleteStoryboardShot("project-1", "shot-1");
    await runtimeClient.listStoryboardTemplates();
    await runtimeClient.syncStoryboardFromScript("project-1");
    await runtimeClient.fetchVideoStages("video-1");
    await runtimeClient.rerunVideoStage("video-1", "extract_structure");

    expect(calls).toEqual([
      {
        path: "/api/scripts/projects/project-1/title-variants",
        method: "POST",
        body: { topic: "短视频开场钩子", count: 3 }
      },
      { path: "/api/scripts/projects/project-1/versions", method: "GET", body: undefined },
      {
        path: "/api/scripts/projects/project-1/restore/version-2",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/scripts/projects/project-1/segments/segment-1/rewrite",
        method: "POST",
        body: { instructions: "改得更有冲击力" }
      },
      {
        path: "/api/prompt-templates?kind=script_segment_rewrite",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/prompt-templates",
        method: "POST",
        body: {
          kind: "script_segment_rewrite",
          name: "强钩子",
          description: "用于强化短视频开场钩子",
          content: "请把这一段改得更抓人。"
        }
      },
      {
        path: "/api/prompt-templates/template-1",
        method: "PUT",
        body: {
          kind: "script_segment_rewrite",
          name: "强钩子 v2",
          description: "用于强化短视频开场钩子",
          content: "请把这一段改得更有冲击力。"
        }
      },
      { path: "/api/prompt-templates/template-1", method: "DELETE", body: undefined },
      {
        path: "/api/storyboards/projects/project-1/shots",
        method: "POST",
        body: {
          title: "开场镜头",
          summary: "镜头推进产品",
          visualPrompt: "竖屏，快速推进"
        }
      },
      {
        path: "/api/storyboards/projects/project-1/shots/shot-1",
        method: "PATCH",
        body: { title: "开场特写" }
      },
      {
        path: "/api/storyboards/projects/project-1/shots/shot-1",
        method: "DELETE",
        body: undefined
      },
      { path: "/api/storyboards/templates", method: "GET", body: undefined },
      {
        path: "/api/storyboards/projects/project-1/sync-from-script",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/video-deconstruction/videos/video-1/stages",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/video-deconstruction/videos/video-1/stages/extract_structure/rerun",
        method: "POST",
        body: undefined
      }
    ]);
  });

  it("keeps existing canonical B-S3 endpoints stable", async () => {
    const calls: Array<{ method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        calls.push({ path, method });
        return okJsonResponse(sampleResponse(path, method));
      })
    );

    await fetchScriptDocument("project-1");
    await extractVideoStructure("video-1");
    await fetchVideoStructure("video-1");
    await applyVideoExtractionToProject("extraction-1");

    expect(calls).toEqual([
      { path: "/api/scripts/projects/project-1/document", method: "GET" },
      { path: "/api/video-deconstruction/videos/video-1/extract-structure", method: "POST" },
      { path: "/api/video-deconstruction/videos/video-1/structure", method: "GET" },
      {
        path: "/api/video-deconstruction/extractions/extraction-1/apply-to-project",
        method: "POST"
      }
    ]);
  });
});

function sampleResponse(path: string, method: string): unknown {
  if (path.includes("/title-variants")) {
    return [{ id: "variant-1", title: "更强开场", adopted: false }];
  }
  if (path.includes("/versions")) {
    return [
      {
        revision: 2,
        source: "manual",
        content: "脚本版本",
        provider: null,
        model: null,
        aiJobId: null,
        createdAt: "2026-04-17T12:00:00Z"
      }
    ];
  }
  if (path.includes("/restore/")) {
    return scriptDocument();
  }
  if (path.includes("/segments/")) {
    return {
      id: "segment-1",
      segmentId: "segment-1",
      title: "第一段",
      content: "重写后的段落"
    };
  }
  if (path.startsWith("/api/prompt-templates") && method === "GET") {
    return [promptTemplate()];
  }
  if (path.startsWith("/api/prompt-templates") && method === "DELETE") {
    return undefined;
  }
  if (path.startsWith("/api/prompt-templates")) {
    return promptTemplate();
  }
  if (path.includes("/shots")) {
    if (method === "DELETE") {
      return undefined;
    }
    return storyboardShot();
  }
  if (path === "/api/storyboards/templates") {
    return [{ id: "template-1", name: "节奏模板", sceneCount: 3 }];
  }
  if (path.endsWith("/sync-from-script")) {
    return storyboardDocument();
  }
  if (path.endsWith("/stages")) {
    return [{ stage: "extract_structure", status: "ready", progressPct: 100 }];
  }
  if (path.includes("/rerun")) {
    return {
      id: "task-1",
      kind: "video_import",
      label: "重跑阶段",
      status: "queued",
      progressPct: 0,
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:00:00Z"
    };
  }
  if (path.endsWith("/document")) {
    return scriptDocument();
  }
  if (path.endsWith("/extract-structure") || path.endsWith("/structure")) {
    return {
      id: "extraction-1",
      videoId: "video-1",
      status: "ready",
      scriptJson: "{}",
      storyboardJson: "{}",
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:00:00Z"
    };
  }
  if (path.endsWith("/apply-to-project")) {
    return {
      projectId: "project-1",
      extractionId: "extraction-1",
      scriptRevision: 3,
      status: "applied",
      message: "已回流到脚本"
    };
  }
  return {};
}

function scriptDocument() {
  return {
    projectId: "project-1",
    currentVersion: {
      revision: 3,
      source: "manual",
      content: "脚本文本",
      provider: null,
      model: null,
      aiJobId: null,
      createdAt: "2026-04-17T12:00:00Z"
    },
    versions: [],
    recentJobs: []
  };
}

function promptTemplate() {
  return {
    id: "template-1",
    kind: "script_segment_rewrite",
    name: "强钩子",
    description: "用于强化短视频开场钩子",
    content: "请把这一段改得更抓人。",
    createdAt: "2026-04-17T12:00:00Z",
    updatedAt: "2026-04-17T12:00:00Z"
  };
}

function storyboardShot() {
  return {
    id: "shot-1",
    title: "开场镜头",
    summary: "镜头推进产品",
    visualPrompt: "竖屏，快速推进",
    orderIndex: 0
  };
}

function storyboardDocument() {
  return {
    projectId: "project-1",
    basedOnScriptRevision: 3,
    currentVersion: {
      revision: 1,
      basedOnScriptRevision: 3,
      source: "manual",
      scenes: [],
      provider: null,
      model: null,
      aiJobId: null,
      createdAt: "2026-04-17T12:00:00Z"
    },
    versions: [],
    recentJobs: []
  };
}
