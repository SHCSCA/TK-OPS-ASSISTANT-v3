import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceAIActions from "@/modules/workspace/WorkspaceAIActions.vue";
import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type { WorkspaceTimelineClipDto } from "@/types/runtime";

function mountActions(options: {
  blockedMessage?: string | null;
  hasTimeline?: boolean;
  selectedClip?: WorkspaceTimelineClipDto | null;
  status?: EditingWorkspaceStatus;
}) {
  return mount(WorkspaceAIActions, {
    props: {
      blockedMessage: options.blockedMessage ?? null,
      hasTimeline: options.hasTimeline ?? true,
      selectedClip: options.selectedClip ?? null,
      status: options.status ?? "ready"
    }
  });
}

describe("WorkspaceAIActions", () => {
  it("用当前智能粗剪交付语义渲染不同状态", () => {
    const blocked = mountActions({
      blockedMessage: "智能粗剪暂不可用：智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。",
      status: "blocked"
    });
    expect(blocked.text()).toContain("智能粗剪");
    expect(blocked.text()).toContain("已阻断");
    expect(blocked.text()).toContain("智能粗剪能力未启用");

    const loading = mountActions({ status: "loading" });
    expect(loading.text()).toContain("处理中");

    const waiting = mountActions({ hasTimeline: false });
    expect(waiting.text()).toContain("等待时间线");

    const ready = mountActions({ status: "ready" });
    expect(ready.text()).toContain("可用");
    expect(ready.text()).not.toContain("AI 魔法剪");
    expect(ready.text()).not.toContain("Blocked");
    expect(ready.text()).not.toContain("Disabled");
    expect(ready.text()).not.toContain("Ready");
  });
});
