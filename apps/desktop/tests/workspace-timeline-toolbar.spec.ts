import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceTimelineToolbar from "../src/modules/workspace/WorkspaceTimelineToolbar.vue";

describe("M05 时间线基础工具栏", () => {
  it("仅在选中片段后开放分割和删除动作", async () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "选择工具 · 磁吸开启",
        disabled: false,
        canSplit: true,
        canDelete: true,
        canMove: true,
        canTrim: true
      }
    });

    const splitButton = wrapper.get('[data-testid="workspace-tool-split"]');
    const deleteButton = wrapper.get('[data-testid="workspace-tool-delete"]');

    expect((splitButton.element as HTMLButtonElement).disabled).toBe(false);
    expect((deleteButton.element as HTMLButtonElement).disabled).toBe(false);

    await splitButton.trigger("click");
    await deleteButton.trigger("click");

    expect(wrapper.emitted("split")).toHaveLength(1);
    expect(wrapper.emitted("delete")).toHaveLength(1);
  });

  it("开放移动和裁剪步进动作", async () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        canSplit: true,
        canDelete: true,
        canMove: true,
        canTrim: true
      }
    });

    await wrapper.get('[data-testid="workspace-tool-move-left"]').trigger("click");
    await wrapper.get('[data-testid="workspace-tool-trim-right"]').trigger("click");

    expect(wrapper.emitted("move")).toEqual([[-500]]);
    expect(wrapper.emitted("trim")).toEqual([["right", -500]]);
  });

  it("有上一版时间线时开放撤销动作", async () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        canSplit: true,
        canDelete: true,
        canMove: true,
        canTrim: true,
        canUndo: true
      }
    });

    const undoButton = wrapper.get('[data-testid="workspace-tool-undo"]');
    expect(undoButton.text()).toContain("撤销");
    expect((undoButton.element as HTMLButtonElement).disabled).toBe(false);

    await undoButton.trigger("click");

    expect(wrapper.emitted("undo")).toHaveLength(1);
  });

  it("撤销后开放重做动作", async () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        canRedo: true
      }
    });

    const redoButton = wrapper.get('[data-testid="workspace-tool-redo"]');
    expect(redoButton.text()).toContain("重做");
    expect((redoButton.element as HTMLButtonElement).disabled).toBe(false);

    await redoButton.trigger("click");

    expect(wrapper.emitted("redo")).toHaveLength(1);
  });

  it("缩放控件开放缩小、放大和滑块档位", async () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        zoomPercent: 100
      }
    });

    const zoomRegion = wrapper.get('[data-testid="workspace-timeline-zoom"]');
    expect(zoomRegion.attributes("aria-disabled")).toBeUndefined();
    expect(wrapper.get('[data-testid="workspace-timeline-zoom-value"]').text()).toBe("100%");

    await wrapper.get('[data-testid="workspace-timeline-zoom-in"]').trigger("click");
    await wrapper.get('[data-testid="workspace-timeline-zoom-out"]').trigger("click");

    const slider = wrapper.get('[data-testid="workspace-timeline-zoom-slider"]');
    await slider.setValue("200");

    expect(wrapper.emitted("zoom-change")).toEqual([[150], [75], [200]]);
  });

  it("缩放控件在边界档位禁用对应方向", () => {
    const minWrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        zoomPercent: 50
      }
    });
    const maxWrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "片段：clip-1",
        disabled: false,
        zoomPercent: 300
      }
    });

    expect((minWrapper.get('[data-testid="workspace-timeline-zoom-out"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((maxWrapper.get('[data-testid="workspace-timeline-zoom-in"]').element as HTMLButtonElement).disabled).toBe(true);
  });

  it("忙碌或未选中片段时保持危险动作禁用", () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "等待时间线",
        disabled: true,
        canSplit: false,
        canDelete: false,
        canMove: false,
        canTrim: false
      }
    });

    expect((wrapper.get('[data-testid="workspace-tool-split"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-delete"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-move-left"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-trim-right"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-undo"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-redo"]').element as HTMLButtonElement).disabled).toBe(true);
  });
});
