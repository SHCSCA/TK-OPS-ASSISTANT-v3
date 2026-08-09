import { useEffect, useMemo, useState } from "react";
import { configBus } from "../config/configBus.js";
import { prototypeConfig } from "../config/prototypeConfig.js";
import { cloneAccountWorkspaces } from "../data/accounts.js";
import { buildGenerationSteps, cloneGenerationRuns } from "../data/generationRuns.js";
import { prototypeLogger } from "../utils/logger.js";

const initialPageByAccount = { mirror: "workspace", focus: "workspace" };

export function useWorkspaceState() {
  const [workspaces, setWorkspaces] = useState(cloneAccountWorkspaces);
  const [activeAccountId, setActiveAccountId] = useState("mirror");
  const [activePage, setActivePage] = useState("workspace");
  const [lastPageByAccount, setLastPageByAccount] = useState(initialPageByAccount);
  const [stageFilter, setStageFilter] = useState(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [switching, setSwitching] = useState(false);
  const [toast, setToast] = useState(null);
  const [theme, setTheme] = useState(configBus.loadTheme);
  const [pageState, setPageState] = useState("ready");
  const [dataScenario, setDataScenario] = useState("seeded");
  const [generationRuns, setGenerationRuns] = useState(cloneGenerationRuns);

  const workspace = workspaces[activeAccountId];
  const accounts = useMemo(
    () => Object.values(workspaces).map((item) => item.account),
    [workspaces],
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    configBus.saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function notify(message, tone = "success") {
    setToast({ id: Date.now(), message, tone });
  }

  function navigate(pageId) {
    setActivePage(pageId);
    setLastPageByAccount((current) => ({ ...current, [activeAccountId]: pageId }));
    setAccountMenuOpen(false);
    setDetail(null);
  }

  async function switchAccount(accountId) {
    if (accountId === activeAccountId || switching) return;
    setSwitching(true);
    setAccountMenuOpen(false);
    setStageFilter(null);
    setDetail(null);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.accountSwitchDelay));
      setActiveAccountId(accountId);
      setActivePage(lastPageByAccount[accountId] || "workspace");
      setPageState("ready");
      prototypeLogger.info("账号工作区已切换", { accountId });
      notify(`已切换到 ${workspaces[accountId].account.name}`);
    } catch (error) {
      prototypeLogger.error("账号切换失败", error);
      notify("账号切换失败，请重试", "danger");
    } finally {
      setSwitching(false);
    }
  }

  async function createBatch(form) {
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
      const batch = {
        id: `${activeAccountId}-batch-${Date.now()}`,
        name: form.name,
        stage: "选题",
        progress: 8,
        status: "running",
        updated: "刚刚",
        items: Number(form.count),
        inputMode: form.mode,
        recipe: form.recipe,
      };
      setWorkspaces((current) => ({
        ...current,
        [activeAccountId]: {
          ...current[activeAccountId],
          batches: [batch, ...current[activeAccountId].batches],
        },
      }));
      setGenerationRuns((current) => ({
        ...current,
        [batch.id]: {
          batchId: batch.id,
          mode: form.mode,
          recipe: form.recipe,
          knowledgeSnapshot: `${workspace.account.name} · 演示知识快照`,
          positioningVersion: workspace.strategy.version,
          steps: buildGenerationSteps(form.mode, false),
        },
      }));
      setBatchDialogOpen(false);
      setStageFilter(null);
      prototypeLogger.info("演示批次已创建", { accountId: activeAccountId, batchId: batch.id });
      notify("批次已创建，已进入选题阶段");
      return true;
    } catch (error) {
      prototypeLogger.error("创建批次失败", error);
      notify("创建批次失败，请检查后重试", "danger");
      return false;
    }
  }

  function registerAccountWorkspace(profile) {
    try {
      setWorkspaces((current) => {
        if (current[profile.id]) return current;
        return {
          ...current,
          [profile.id]: {
            account: { id: profile.id, initials: profile.initials, name: profile.name, platform: profile.platform, positioning: profile.shortPositioning, status: "online" },
            strategy: { summary: profile.positioning, version: "定位 v1", pillars: ["待完善"], rules: ["内容仅属于当前账号"] },
            knowledge: [{ id: `${profile.id}-k1`, type: "账号空间", name: "独立知识空间", status: "ready", updated: "刚刚" }],
            topics: [], batches: [], exceptions: [], variants: [], library: [], publishing: [], review: [],
          },
        };
      });
      setLastPageByAccount((current) => ({ ...current, [profile.id]: "workspace" }));
      prototypeLogger.info("新账号工作区已注册", { accountId: profile.id });
    } catch (error) {
      prototypeLogger.error("注册账号工作区失败", error);
      notify("账号工作区初始化失败，请重试", "danger");
    }
  }

  function updateGenerationStep(batchId, stepId, updater) {
    setGenerationRuns((current) => {
      const run = current[batchId];
      if (!run) return current;
      return { ...current, [batchId]: { ...run, steps: run.steps.map((step) => step.id === stepId ? updater(step) : step) } };
    });
  }

  function retryGenerationStep(batchId, stepId) {
    try {
      updateGenerationStep(batchId, stepId, (step) => ({ ...step, status: "running", progress: 12, error: null, attempts: step.attempts + 1, duration: "运行中" }));
      setDetail(null);
      prototypeLogger.info("AI 节点已局部重试", { batchId, stepId });
      notify("失败节点已从最小范围重新排队", "info");
    } catch (error) {
      prototypeLogger.error("AI 节点重试失败", error);
      notify("节点重试失败，请查看日志", "danger");
    }
  }

  function fallbackGenerationStep(batchId, stepId) {
    updateGenerationStep(batchId, stepId, (step) => ({ ...step, model: "回退模型 · 演示", status: "queued", progress: 0, error: null }));
    setDetail(null);
    prototypeLogger.info("AI 节点已切换回退模型", { batchId, stepId });
    notify("已选择演示回退模型，节点重新排队", "info");
  }

  function cancelGenerationStep(batchId, stepId) {
    updateGenerationStep(batchId, stepId, (step) => ({ ...step, status: "cancelling", duration: "正在取消" }));
    prototypeLogger.info("AI 节点正在取消", { batchId, stepId });
    notify("取消请求已发送，等待节点确认", "info");
  }

  async function retryException(exceptionId) {
    const target = workspace.exceptions.find((item) => item.id === exceptionId);
    if (!target) return;
    notify(`正在处理：${target.title}`, "info");
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
      setWorkspaces((current) => ({
        ...current,
        [activeAccountId]: {
          ...current[activeAccountId],
          exceptions: current[activeAccountId].exceptions.filter((item) => item.id !== exceptionId),
        },
      }));
      setDetail(null);
      prototypeLogger.info("异常已恢复", { accountId: activeAccountId, exceptionId });
      notify("异常已恢复，批次状态已刷新");
    } catch (error) {
      prototypeLogger.error("异常恢复失败", error);
      notify("恢复失败，请查看日志后重试", "danger");
    }
  }

  async function retryBatch(batchId) {
    try {
      setWorkspaces((current) => ({
        ...current,
        [activeAccountId]: {
          ...current[activeAccountId],
          batches: current[activeAccountId].batches.map((batch) =>
            batch.id === batchId
              ? { ...batch, status: "running", progress: Math.max(batch.progress, 30), updated: "刚刚" }
              : batch,
          ),
        },
      }));
      prototypeLogger.info("批次已重试", { accountId: activeAccountId, batchId });
      notify("失败阶段已重新排队");
    } catch (error) {
      prototypeLogger.error("批次重试失败", error);
      notify("批次重试失败", "danger");
    }
  }

  function toggleTopic(topicId) {
    setWorkspaces((current) => ({
      ...current,
      [activeAccountId]: {
        ...current[activeAccountId],
        topics: current[activeAccountId].topics.map((topic) =>
          topic.id === topicId ? { ...topic, selected: !topic.selected } : topic,
        ),
      },
    }));
  }

  function updateKnowledge(sourceId) {
    setWorkspaces((current) => ({
      ...current,
      [activeAccountId]: {
        ...current[activeAccountId],
        knowledge: current[activeAccountId].knowledge.map((source) =>
          source.id === sourceId ? { ...source, status: "ready", updated: "刚刚" } : source,
        ),
      },
    }));
    notify("知识来源已重新索引");
  }

  return {
    accounts,
    accountMenuOpen,
    activeAccountId,
    activePage,
    batchDialogOpen,
    createBatch,
    cancelGenerationStep,
    detail,
    dataScenario,
    fallbackGenerationStep,
    generationRuns,
    navigate,
    notify,
    pageState,
    registerAccountWorkspace,
    retryBatch,
    retryException,
    retryGenerationStep,
    setAccountMenuOpen,
    setBatchDialogOpen,
    setDetail,
    setDataScenario,
    setPageState,
    setStageFilter,
    setTheme,
    stageFilter,
    switching,
    switchAccount,
    theme,
    toggleTopic,
    updateKnowledge,
    workspace,
  };
}
