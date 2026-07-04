import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceMagicCutSuggestions from "../src/modules/workspace/WorkspaceMagicCutSuggestions.vue";
import type { MagicCutSuggestionDraftDto } from "../src/types/runtime";

describe("WorkspaceMagicCutSuggestions", () => {
  it("显示待审阅标题并支持选中应用、全部应用、单条应用、定位和忽略", async () => {
    const wrapper = mount(WorkspaceMagicCutSuggestions, {
      props: {
        suggestion: suggestionDraft(),
        status: "ready",
        errorMessage: null
      }
    });

    expect(wrapper.text()).toContain("AI 粗剪建议 · 2 条待审阅");
    expect(wrapper.text()).toContain("应用后将修改当前时间线，可通过撤销恢复。");

    await wrapper.get('[data-testid="magic-cut-operation-operation-trim-1"] input').setValue(false);
    await wrapper.get('[data-testid="magic-cut-apply-selected"]').trigger("click");
    expect(wrapper.emitted("apply")).toEqual([[["operation-delete-1"]]]);

    await wrapper.get('[data-testid="magic-cut-apply-all"]').trigger("click");
    expect(wrapper.emitted("apply")?.at(-1)).toEqual([[]]);

    await wrapper.get('[data-testid="magic-cut-apply-one-operation-trim-1"]').trigger("click");
    expect(wrapper.emitted("apply")?.at(-1)).toEqual([["operation-trim-1"]]);

    await wrapper.get('[data-testid="magic-cut-focus-operation-trim-1"]').trigger("click");
    expect(wrapper.emitted("focus")).toEqual([[{ clipId: "clip-opening", trackId: "track-video" }]]);

    await wrapper.get('[data-testid="magic-cut-dismiss"]').trigger("click");
    expect(wrapper.emitted("dismiss")).toEqual([[]]);
  });

  it("覆盖加载、空、应用中、错误和重读入口", async () => {
    const wrapper = mount(WorkspaceMagicCutSuggestions, {
      props: {
        suggestion: null,
        status: "loading",
        errorMessage: null
      }
    });

    expect(wrapper.text()).toContain("正在读取智能粗剪建议");

    await wrapper.setProps({ status: "ready" });
    expect(wrapper.text()).toContain("暂无可应用建议。");

    await wrapper.setProps({ suggestion: suggestionDraft(), status: "applying" });
    expect(wrapper.text()).toContain("正在应用建议");
    expect((wrapper.get('[data-testid="magic-cut-apply-all"]').element as HTMLButtonElement).disabled).toBe(true);

    await wrapper.setProps({
      errorMessage: "时间线已变化，请重新生成智能粗剪建议。",
      status: "error",
      suggestion: suggestionDraft()
    });
    expect(wrapper.text()).toContain("时间线已变化，请重新生成智能粗剪建议。");
    await wrapper.get('[data-testid="magic-cut-reload"]').trigger("click");
    expect(wrapper.emitted("reload")).toEqual([[]]);
  });

  it("failed_parse 草稿显示重新生成入口，不显示应用按钮", async () => {
    const wrapper = mount(WorkspaceMagicCutSuggestions, {
      props: {
        suggestion: {
          ...suggestionDraft(),
          status: "failed_parse",
          operations: [],
          summary: "AI 返回内容无法生成建议，请重新生成"
        },
        status: "ready",
        errorMessage: null
      }
    });

    expect(wrapper.text()).toContain("AI 返回内容无法生成建议，请重新生成");
    await wrapper.get('[data-testid="magic-cut-regenerate"]').trigger("click");
    expect(wrapper.emitted("regenerate")).toEqual([[]]);
    expect(wrapper.find('[data-testid="magic-cut-apply-all"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="magic-cut-apply-selected"]').exists()).toBe(false);
  });

  it("保留紧凑面板布局结构，按钮可换行且列表独立滚动", () => {
    const wrapper = mount(WorkspaceMagicCutSuggestions, {
      props: {
        suggestion: suggestionDraft(),
        status: "ready",
        errorMessage: null
      }
    });

    expect(wrapper.get('[data-testid="magic-cut-suggestions"]').classes()).toContain(
      "workspace-magic-cut-suggestions"
    );
    expect(wrapper.get('[data-testid="magic-cut-operation-list"]').classes()).toContain(
      "workspace-magic-cut-suggestions__list"
    );
    expect(wrapper.get('[data-testid="magic-cut-bulk-actions"]').classes()).toContain(
      "workspace-magic-cut-suggestions__actions"
    );
  });
});

function suggestionDraft(): MagicCutSuggestionDraftDto {
  return {
    id: "suggestion-1",
    projectId: "project-1",
    timelineId: "timeline-1",
    timelineVersionToken: "sha256:timeline-token",
    status: "pending_review",
    summary: "建议压缩开场并删除冗余片段。",
    operations: [
      {
        id: "operation-trim-1",
        action: "trim",
        clipId: "clip-opening",
        trackId: "track-video",
        targetTrackId: null,
        originalStartMs: 0,
        originalDurationMs: 4200,
        suggestedStartMs: 0,
        suggestedDurationMs: 3000,
        splitAtMs: null,
        reason: "开场停顿过长。",
        risk: null
      },
      {
        id: "operation-delete-1",
        action: "delete",
        clipId: "clip-pause",
        trackId: "track-video",
        targetTrackId: null,
        originalStartMs: 5200,
        originalDurationMs: 900,
        suggestedStartMs: null,
        suggestedDurationMs: null,
        splitAtMs: null,
        reason: "此处重复停顿影响节奏。",
        risk: "删除后需复核字幕衔接。"
      }
    ],
    createdAt: "2026-07-04T10:00:00Z",
    updatedAt: "2026-07-04T10:00:00Z",
    appliedAt: null
  };
}
