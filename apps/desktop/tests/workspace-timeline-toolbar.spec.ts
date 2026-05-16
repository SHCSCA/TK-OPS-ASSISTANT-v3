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
        canDelete: true
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

  it("忙碌或未选中片段时保持危险动作禁用", () => {
    const wrapper = mount(WorkspaceTimelineToolbar, {
      props: {
        statusLabel: "等待时间线",
        disabled: true,
        canSplit: false,
        canDelete: false
      }
    });

    expect((wrapper.get('[data-testid="workspace-tool-split"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-testid="workspace-tool-delete"]').element as HTMLButtonElement).disabled).toBe(true);
  });
});
