import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceCommandFeedbackBar from "../src/modules/workspace/WorkspaceCommandFeedbackBar.vue";
import type { WorkspaceAICommandResultDto } from "../src/types/runtime";
import type { TaskInfo } from "../src/types/task-events";

describe("WorkspaceCommandFeedback", () => {
  it("运行中的智能粗剪任务显示进度并允许取消", async () => {
    const task = taskInfo({
      id: "task-magic-cut-1",
      status: "running",
      progress: 42,
      message: "正在分析时间线节奏。"
    });

    const wrapper = mount(WorkspaceCommandFeedbackBar, {
      props: {
        activeTask: task,
        lastCommandResult: null
      }
    });

    expect(wrapper.get('[data-testid="workspace-command-feedback"]').text()).toContain("智能粗剪处理中");
    expect(wrapper.text()).toContain("正在分析时间线节奏。");
    expect(wrapper.get('[data-testid="workspace-command-progress"]').attributes("aria-valuenow")).toBe("42");

    await wrapper.get('[data-testid="workspace-command-cancel-button"]').trigger("click");

    expect(wrapper.emitted("cancel")).toEqual([["task-magic-cut-1"]]);
  });

  it("失败的智能粗剪结果显示原因并允许重试", async () => {
    const result: WorkspaceAICommandResultDto = {
      status: "failed",
      task: taskInfo({
        id: "task-magic-cut-2",
        status: "failed",
        progress: 68,
        message: "当前 AI 能力已停用。"
      }),
      message: "当前 AI 能力已停用。"
    };

    const wrapper = mount(WorkspaceCommandFeedbackBar, {
      props: {
        activeTask: null,
        lastCommandResult: result
      }
    });

    expect(wrapper.text()).toContain("智能粗剪失败");
    expect(wrapper.text()).toContain("当前 AI 能力已停用。");

    await wrapper.get('[data-testid="workspace-command-retry-button"]').trigger("click");

    expect(wrapper.emitted("retry")).toEqual([[]]);
  });

  it("取消后的智能粗剪结果保留恢复入口", async () => {
    const result: WorkspaceAICommandResultDto = {
      status: "cancelled",
      task: taskInfo({
        id: "task-magic-cut-3",
        status: "cancelled",
        progress: 12,
        message: "智能粗剪任务已取消。"
      }),
      message: "智能粗剪任务已取消。"
    };

    const wrapper = mount(WorkspaceCommandFeedbackBar, {
      props: {
        activeTask: null,
        lastCommandResult: result,
        cancelPending: true
      }
    });

    expect(wrapper.text()).toContain("智能粗剪已取消");
    expect(wrapper.get('[data-testid="workspace-command-retry-button"]').text()).toContain("重新智能粗剪");
    expect(wrapper.find('[data-testid="workspace-command-cancel-button"]').exists()).toBe(false);
  });

  it("排队结果缺少任务 id 时不显示无效取消入口", () => {
    const wrapper = mount(WorkspaceCommandFeedbackBar, {
      props: {
        activeTask: null,
        lastCommandResult: {
          status: "queued",
          task: null,
          message: "智能粗剪已提交，等待 Runtime 返回任务编号。"
        }
      }
    });

    expect(wrapper.text()).toContain("智能粗剪排队中");
    expect(wrapper.find('[data-testid="workspace-command-cancel-button"]').exists()).toBe(false);
  });
});

function taskInfo(overrides: Partial<TaskInfo>): TaskInfo {
  return {
    id: "task-magic-cut",
    task_type: "ai-workspace-command",
    project_id: "project-1",
    status: "queued",
    progress: 0,
    message: "AI 命令已进入任务队列。",
    created_at: "2026-04-17T10:00:00Z",
    updated_at: "2026-04-17T10:00:00Z",
    ...overrides
  };
}
