import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { open } from "@tauri-apps/plugin-dialog";
import { convertFileSrc } from "@tauri-apps/api/core";

import AssetDetail from "@/components/shell/details/AssetDetail.vue";
import AssetLibraryPage from "@/pages/assets/AssetLibraryPage.vue";
import { useAssetLibraryStore } from "@/stores/asset-library";
import { useShellUiStore } from "@/stores/shell-ui";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn()
}));

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: vi.fn((filePath: string) => `asset://local/${encodeURIComponent(filePath)}`),
  isTauri: vi.fn(() => true)
}));

describe("M09 资产中心页面体验", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(window, "alert").mockImplementation(() => undefined);
    vi.mocked(open).mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("展示素材操作带、排序入口和真实素材墙，选择资产后打开右侧抽屉", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/assets" && method === "GET") return okJsonResponse([asset()]);
        if (path === "/api/assets/asset-1/references") return okJsonResponse([assetReference()]);
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, shellUiStore } = mountAssetLibrary();
    await flushPromises();

    expect(wrapper.text()).toContain("M09 资产中心");
    expect(wrapper.find('input[placeholder="搜索资产名称、标签或来源"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("最新导入");
    expect(wrapper.text()).toContain("Clip");

    await wrapper.get('[data-testid="asset-card-asset-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="asset-card-asset-1"]').classes()).toContain("asset-card--selected");
    expect(shellUiStore.isDetailPanelOpen).toBe(true);
    expect(shellUiStore.detailContext.title).toBe("Clip");
    expect(window.alert).not.toHaveBeenCalled();
  });

  it("基于真实资产结果展示分组摘要和当前选择，不补假统计", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/assets" && method === "GET") {
          return okJsonResponse([
            asset("asset-video", "opening.mp4", "video", "D:/tkops/assets/opening.mp4"),
            asset("asset-image", "cover.jpg", "image", "D:/tkops/assets/cover.jpg"),
            asset("asset-document", "brief.pdf", "document", "D:/tkops/assets/brief.pdf")
          ]);
        }
        if (path === "/api/assets/asset-image/references") return okJsonResponse([]);
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, shellUiStore } = mountAssetLibrary();
    await flushPromises();

    expect(wrapper.findAll('[data-testid^="asset-card-"]')).toHaveLength(3);
    expect(wrapper.text()).toContain("当前结果");

    await wrapper.get('[data-testid="asset-card-asset-image"]').trigger("click");
    await flushPromises();

    expect(shellUiStore.detailContext.title).toBe("cover.jpg");
    expect(shellUiStore.detailContext.mode).toBe("asset");
  });

  it("点击导入支持批量选择、同批去重、自动选中新资产并打开详情抽屉", async () => {
    vi.mocked(open).mockResolvedValue([
      "D:/tkops/assets/batch-a.mp4",
      "D:/tkops/assets/batch-a.mp4",
      "D:/tkops/assets/batch-b.jpg"
    ]);
    const importBodies: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        if (path === "/api/assets" && method === "GET") return okJsonResponse([]);
        if (path === "/api/assets/import" && method === "POST") {
          const body = JSON.parse(String(init?.body));
          importBodies.push(body);
          return okJsonResponse(
            asset(
              `asset-${importBodies.length + 1}`,
              String(body.filePath).split("/").pop(),
              body.type,
              body.filePath
            )
          );
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper, assetStore, shellUiStore } = mountAssetLibrary();
    await flushPromises();

    await wrapper.get('[data-testid="asset-import-button"]').trigger("click");
    await waitForMicrotasks();

    expect(open).toHaveBeenCalledWith(expect.objectContaining({ multiple: true }));
    expect(importBodies).toEqual([
      { filePath: "D:/tkops/assets/batch-a.mp4", type: "video", source: "local" },
      { filePath: "D:/tkops/assets/batch-b.jpg", type: "image", source: "local" }
    ]);
    expect(wrapper.text()).toContain("已导入 2 个真实本地资产");
    expect(wrapper.text()).toContain("跳过 1 个重复路径");
    expect(assetStore.selectedId).toBe("asset-3");
    expect(shellUiStore.isDetailPanelOpen).toBe(true);
  });

  it("拖拽进入时显示文件数量和导入提示，离开后关闭覆盖层", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/assets" && method === "GET") return okJsonResponse([]);
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = mountAssetLibrary();
    await flushPromises();

    expect(wrapper.text()).toContain("当前项目还没有可复用资产");

    await wrapper.get('[data-testid="asset-library"]').trigger("dragover", {
      dataTransfer: {
        items: [{ kind: "file" }, { kind: "file" }]
      }
    });
    expect(wrapper.text()).toContain("松开导入到资产中心");
    expect(wrapper.text()).toContain("2 个本地文件");

    await wrapper.get('[data-testid="asset-library"]').trigger("dragleave");
    expect(wrapper.text()).not.toContain("松开导入到资产中心");
  });

  it("视频、图片、PDF 和未知文档分别使用真实本地文件预览或明确降级态", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/assets" && method === "GET") {
          return okJsonResponse([
            asset("video-1", "opening.mp4", "video", "D:/tkops/assets/opening.mp4"),
            asset("image-1", "cover.jpg", "image", "D:/tkops/assets/cover.jpg"),
            asset("pdf-1", "brief.pdf", "document", "D:/tkops/assets/brief.pdf"),
            asset("doc-1", "notes.docx", "document", "D:/tkops/assets/notes.docx")
          ]);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = mountAssetLibrary();
    await flushPromises();

    expect(wrapper.get('[data-testid="asset-preview-video-video-1"]').attributes("src")).toBe(
      "asset://local/D%3A%2Ftkops%2Fassets%2Fopening.mp4"
    );
    expect(wrapper.get('[data-testid="asset-preview-image-image-1"]').attributes("src")).toBe(
      "asset://local/D%3A%2Ftkops%2Fassets%2Fcover.jpg"
    );
    expect(wrapper.get('[data-testid="asset-preview-document-pdf-1"]').attributes("src")).toBe(
      "asset://local/D%3A%2Ftkops%2Fassets%2Fbrief.pdf"
    );
    expect(wrapper.get('[data-testid="asset-preview-document-sheet-doc-1"]').text()).toContain("暂不支持预览");
    expect(convertFileSrc).toHaveBeenCalledWith("D:/tkops/assets/opening.mp4");
    expect(wrapper.findAll(".asset-preview .material-symbols-outlined")).toHaveLength(0);
  });

  it("文本文档预览按 UTF-8 读取并展示中文内容", async () => {
    const documentText = "第一行：中文脚本\n第二行：UTF-8 文档预览";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const requestUrl = String(input);
      if (requestUrl.startsWith("asset://local/")) {
        return {
          ok: true,
          status: 200,
          text: async () => documentText
        };
      }

      const url = new URL(requestUrl);
      const path = `${url.pathname}${url.search}`;
      const method = (init?.method ?? "GET").toUpperCase();
      if (path === "/api/assets" && method === "GET") {
        return okJsonResponse([
          asset("doc-utf8", "脚本清单.txt", "document", "D:/tkops/assets/脚本清单.txt")
        ]);
      }
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { wrapper } = mountAssetLibrary();
    await waitForMicrotasks();

    const textPreview = wrapper.get('[data-testid="asset-preview-text-doc-utf8"]');

    expect(textPreview.text()).toContain("中文脚本");
    expect(textPreview.text()).toContain("UTF-8 文档预览");
    expect(fetchMock).toHaveBeenCalledWith(
      "asset://local/D%3A%2Ftkops%2Fassets%2F%E8%84%9A%E6%9C%AC%E6%B8%85%E5%8D%95.txt"
    );
  });

  it("详情抽屉展示上海时间和引用影响", async () => {
    const selected = asset(
      "asset-1",
      "opening.mp4",
      "video",
      "D:/tkops/assets/opening.mp4",
      "2026-04-16T10:00:00Z",
      "2026-04-16T10:30:00Z"
    );

    const wrapper = mount(AssetDetail, {
      props: {
        context: {
          key: "asset:opening.mp4",
          mode: "asset",
          source: "asset-library",
          icon: "inventory_2",
          eyebrow: "资产详情",
          title: selected.name,
          description: "真实资产对象、引用影响和本地文件路径同步展示。",
          metrics: [
            { id: "size", label: "大小", value: "24.0 MB" },
            { id: "refs", label: "引用", value: "1" },
            { id: "project", label: "项目", value: selected.projectId || "未归入项目" }
          ],
          sections: [
            {
              id: "source",
              title: "资产来源",
              fields: [
                { id: "path", label: "路径", value: selected.filePath || "", mono: true, multiline: true },
                { id: "created", label: "创建时间", value: "2026-04-16 18:00:00", mono: true },
                { id: "updated", label: "更新时间", value: "2026-04-16 18:30:00", mono: true }
              ]
            },
            {
              id: "references",
              title: "引用影响",
              items: [{ id: "ref-1", title: "storyboard", description: "scene-1", meta: "已引用", tone: "warning" }]
            }
          ]
        }
      }
    });

    expect(wrapper.text()).toContain("2026-04-16 18:00:00");
    expect(wrapper.text()).toContain("2026-04-16 18:30:00");
    expect(wrapper.text()).toContain("storyboard");
  });
});

function mountAssetLibrary() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(AssetLibraryPage, {
    global: {
      plugins: [pinia],
      stubs: {
        ProjectContextGuard: {
          template: "<div><slot /></div>"
        }
      }
    }
  });

  return {
    wrapper,
    assetStore: useAssetLibraryStore(),
    shellUiStore: useShellUiStore()
  };
}

function now() {
  return "2026-04-16T10:00:00Z";
}

function asset(
  id = "asset-1",
  name = "Clip",
  type = "video",
  filePath = "D:/tkops/assets/clip.mp4",
  createdAt = now(),
  updatedAt = now()
) {
  return {
    id,
    name,
    type,
    source: "local",
    filePath,
    fileSizeBytes: 1024,
    durationMs: null,
    thumbnailPath: null,
    tags: '["开场", "产品"]',
    projectId: "project-1",
    metadataJson: null,
    createdAt,
    updatedAt
  };
}

function assetReference() {
  return {
    id: "ref-1",
    assetId: "asset-1",
    referenceType: "storyboard",
    referenceId: "scene-1",
    createdAt: now()
  };
}

async function waitForMicrotasks() {
  for (let index = 0; index < 5; index += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await flushPromises();
  }
}
