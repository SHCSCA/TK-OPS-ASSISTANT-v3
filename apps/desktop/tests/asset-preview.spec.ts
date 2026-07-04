import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import AssetPreview from "@/components/assets/AssetPreview.vue";
import type { AssetDto } from "@/types/runtime";

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: vi.fn((filePath: string) => `asset://local/${encodeURIComponent(filePath)}`)
}));

describe("AssetPreview", () => {
  it("图片预览优先使用本地缩略图路径", () => {
    const wrapper = mount(AssetPreview, {
      props: {
        asset: asset({
          id: "image-asset",
          type: "image",
          filePath: "G:/assets/source.png",
          thumbnailPath: "G:/assets/thumb.jpg"
        })
      }
    });

    expect(wrapper.get('[data-testid="asset-preview-image-image-asset"]').attributes("src")).toBe(
      "asset://local/G%3A%2Fassets%2Fthumb.jpg"
    );
  });

  it("同一个资产 id 更新缩略图后刷新预览地址", async () => {
    const wrapper = mount(AssetPreview, {
      props: {
        asset: asset({
          id: "image-asset",
          type: "image",
          filePath: "G:/assets/source.png",
          thumbnailPath: null
        })
      }
    });

    expect(wrapper.get('[data-testid="asset-preview-image-image-asset"]').attributes("src")).toBe(
      "asset://local/G%3A%2Fassets%2Fsource.png"
    );

    await wrapper.setProps({
      asset: asset({
        id: "image-asset",
        type: "image",
        filePath: "G:/assets/source.png",
        thumbnailPath: "G:/assets/generated-thumb.jpg"
      })
    });

    expect(wrapper.get('[data-testid="asset-preview-image-image-asset"]').attributes("src")).toBe(
      "asset://local/G%3A%2Fassets%2Fgenerated-thumb.jpg"
    );
  });
});

function asset(overrides: Partial<AssetDto> = {}): AssetDto {
  return {
    id: "asset-1",
    name: "素材.png",
    type: "image",
    source: "local",
    filePath: "G:/assets/source.png",
    fileSizeBytes: 1024,
    durationMs: null,
    thumbnailPath: null,
    tags: null,
    projectId: "project-1",
    metadataJson: null,
    sourceInfo: {
      source: "local",
      projectId: "project-1",
      groupId: null,
      filePath: "G:/assets/source.png",
      metadataSummary: {}
    },
    availability: {
      status: "ready",
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
    createdAt: "2026-06-20T00:00:00.000Z",
    updatedAt: "2026-06-20T00:00:00.000Z",
    ...overrides
  };
}
