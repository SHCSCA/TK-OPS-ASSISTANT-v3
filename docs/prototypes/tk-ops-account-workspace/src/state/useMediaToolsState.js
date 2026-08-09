import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../config/prototypeConfig.js";
import {
  canStartMediaTask,
  cloneAccountMediaTasks,
  getMediaTool,
  mediaTaskToLibraryItem,
} from "../data/mediaTools.js";
import { prototypeLogger } from "../utils/logger.js";

const emptyWizard = { open: false, step: 1, toolId: null, input: "", format: "MP4 · H.264", rightsConfirmed: false };

export function useMediaToolsState(activeAccountId, notify) {
  const [tasksByAccount, setTasksByAccount] = useState(cloneAccountMediaTasks);
  const [wizard, setWizard] = useState(emptyWizard);
  const tasks = tasksByAccount[activeAccountId] || [];
  const outputs = useMemo(() => tasks.map(mediaTaskToLibraryItem).filter(Boolean), [tasks]);

  useEffect(() => {
    setWizard(emptyWizard);
  }, [activeAccountId]);

  function updateAccountTasks(updater) {
    setTasksByAccount((current) => ({ ...current, [activeAccountId]: updater(current[activeAccountId] || []) }));
  }

  function openTool(toolId) {
    setWizard({ ...emptyWizard, open: true, toolId });
  }

  function closeWizard() {
    setWizard(emptyWizard);
  }

  function setWizardField(field, value) {
    setWizard((current) => ({ ...current, [field]: value }));
  }

  function nextStep() {
    if (wizard.step === 1 && !wizard.input.trim()) {
      notify("请先填写公开链接或选择本地文件", "danger");
      return;
    }
    setWizard((current) => ({ ...current, step: Math.min(4, current.step + 1) }));
  }

  async function startTask() {
    if (!canStartMediaTask(wizard)) {
      notify("请完成输入，并确认你拥有素材处理权利", "danger");
      return false;
    }
    const tool = getMediaTool(wizard.toolId);
    const taskId = `${activeAccountId}-tool-${Date.now()}`;
    const task = {
      id: taskId,
      toolId: wizard.toolId,
      title: wizard.input,
      status: "queued",
      progress: 0,
      updated: "刚刚",
      output: null,
      outputPath: null,
    };
    try {
      updateAccountTasks((current) => [task, ...current]);
      closeWizard();
      prototypeLogger.info("媒体工具任务已创建", { accountId: activeAccountId, taskId, toolId: wizard.toolId });
      notify(`${tool?.name || "媒体"}任务已进入队列`, "info");
      await new Promise((resolve) => window.setTimeout(resolve, Math.min(420, prototypeConfig.actionDelay)));
      updateAccountTasks((current) => current.map((item) => item.id === taskId ? { ...item, status: "running", progress: 36 } : item));
      return true;
    } catch (error) {
      prototypeLogger.error("创建媒体工具任务失败", error);
      notify("媒体任务创建失败，请重试", "danger");
      return false;
    }
  }

  function completeTask(taskId) {
    updateAccountTasks((current) => current.map((task) => task.id === taskId ? { ...task, status: "completed", progress: 100, output: "1 项演示输出", outputPath: `内容库 / 工具输出 / ${task.title}` } : task));
    notify("演示任务已完成，输出已写入当前账号内容库");
  }

  function cancelTask(taskId) {
    try {
      updateAccountTasks((current) => current.map((task) => task.id === taskId ? { ...task, status: "cancelling", updated: "正在取消" } : task));
      prototypeLogger.info("媒体工具任务正在取消", { accountId: activeAccountId, taskId });
      notify("取消请求已发送，原始文件不会被删除", "info");
    } catch (error) {
      prototypeLogger.error("取消媒体工具任务失败", error);
      notify("取消失败，请重试", "danger");
    }
  }

  function retryTask(taskId) {
    try {
      updateAccountTasks((current) => current.map((task) => task.id === taskId ? { ...task, status: "queued", progress: 0, error: null, updated: "刚刚" } : task));
      prototypeLogger.info("媒体工具任务已重试", { accountId: activeAccountId, taskId });
      notify("失败任务已重新排队", "info");
    } catch (error) {
      prototypeLogger.error("重试媒体工具任务失败", error);
      notify("任务重试失败", "danger");
    }
  }

  return {
    cancelTask,
    closeWizard,
    completeTask,
    nextStep,
    openTool,
    outputs,
    retryTask,
    setWizard,
    setWizardField,
    startTask,
    tasks,
    wizard,
  };
}
