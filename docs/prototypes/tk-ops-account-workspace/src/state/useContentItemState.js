import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../config/prototypeConfig.js";
import { contentStageLabels, createContentItem } from "../data/contentItems.js";
import {
  buildGeneratedScript,
  buildGeneratedStoryboard,
  canConfirmStoryboard,
  canEnterStoryboard,
  getCreativeStageStates,
  updateStoryboardScene,
} from "../data/creativeWorkflow.js";
import { prototypeLogger } from "../utils/logger.js";

const emptyTopicDialog = {
  form: { angle: "", audience: "", pillar: "", sourceLabel: "", targetDuration: 45, title: "" },
  generating: false,
  open: false,
  selectedSuggestionIds: [],
  source: "manual",
  suggestions: [],
  submitting: false,
};

export function useContentItemState({ activeAccountId, navigate, notify, updateActiveWorkflow, workflow }) {
  const [topicDialog, setTopicDialog] = useState(emptyTopicDialog);
  const [scriptDraft, setScriptDraft] = useState({ raw: "", scriptId: null });
  useEffect(() => setTopicDialog(emptyTopicDialog), [activeAccountId]);
  const selectedContentItem = useMemo(
    () => workflow.contentItems.find((item) => item.id === workflow.selectedContentItemId) || workflow.contentItems[0] || null,
    [workflow.contentItems, workflow.selectedContentItemId],
  );
  const selectedScript = useMemo(
    () => workflow.scripts.find((script) => script.contentItemId === selectedContentItem?.id) || null,
    [selectedContentItem?.id, workflow.scripts],
  );
  useEffect(() => setScriptDraft({ raw: selectedScript?.raw || "", scriptId: selectedScript?.id || null }), [activeAccountId, selectedScript?.id, selectedScript?.raw]);
  const selectedStoryboard = useMemo(
    () => workflow.storyboards.find((board) => board.contentItemId === selectedContentItem?.id) || null,
    [selectedContentItem?.id, workflow.storyboards],
  );
  const selectedScene = useMemo(
    () => selectedStoryboard?.scenes.find((scene) => scene.id === workflow.selectedSceneId) || null,
    [selectedStoryboard, workflow.selectedSceneId],
  );
  const stages = useMemo(
    () => getCreativeStageStates(selectedContentItem, selectedScript, selectedStoryboard, workflow.entries, workflow.assets),
    [selectedContentItem, selectedScript, selectedStoryboard, workflow.entries, workflow.assets],
  );

  function selectContentItem(contentItemId) {
    updateActiveWorkflow((current) => ({ ...current, selectedContentItemId: contentItemId, selectedSceneId: null }));
  }

  function openTopicDialog(source = "manual") {
    setTopicDialog({ ...emptyTopicDialog, form: { ...emptyTopicDialog.form, pillar: source === "manual" ? "工具拆解" : "" }, open: true, source });
  }

  function closeTopicDialog() {
    setTopicDialog(emptyTopicDialog);
  }

  function setTopicDialogField(field, value) {
    setTopicDialog((current) => ({ ...current, form: { ...current.form, [field]: value } }));
  }

  function setTopicSource(source) {
    setTopicDialog((current) => ({ ...current, source }));
  }

  async function generateTopicSuggestions() {
    try {
      setTopicDialog((current) => ({ ...current, generating: true }));
      notify("正在按当前账号定位生成选题候选", "info");
      await delay();
      const suggestions = buildSuggestions(activeAccountId);
      setTopicDialog((current) => ({ ...current, generating: false, selectedSuggestionIds: [suggestions[0].id], suggestions }));
      notify("已生成 3 个选题候选，请选择采用");
    } catch (error) {
      prototypeLogger.error("生成选题候选失败", { accountId: activeAccountId, error });
      setTopicDialog((current) => ({ ...current, generating: false }));
      notify("选题候选生成失败，可重试并查看日志", "danger");
    }
  }

  function toggleTopicSuggestion(id) {
    setTopicDialog((current) => ({
      ...current,
      selectedSuggestionIds: current.selectedSuggestionIds.includes(id)
        ? current.selectedSuggestionIds.filter((item) => item !== id)
        : [...current.selectedSuggestionIds, id],
    }));
  }

  async function submitTopicDialog(deconstructionSelection = null) {
    try {
      setTopicDialog((current) => ({ ...current, submitting: true }));
      await delay();
      const now = Date.now();
      let drafts = [];
      if (topicDialog.source === "ai") {
        drafts = topicDialog.suggestions.filter((item) => topicDialog.selectedSuggestionIds.includes(item.id));
      } else if (topicDialog.source === "deconstruction" && deconstructionSelection) {
        drafts = [deconstructionSelection];
      } else {
        if (!topicDialog.form.title.trim() || !topicDialog.form.pillar) {
          setTopicDialog((current) => ({ ...current, submitting: false }));
          notify("请填写选题标题并选择内容支柱", "danger");
          return false;
        }
        drafts = [{ ...topicDialog.form, sourceLabel: topicDialog.form.sourceLabel || "手动创建", sourceType: "manual", tags: [] }];
      }
      if (!drafts.length) {
        setTopicDialog((current) => ({ ...current, submitting: false }));
        notify("请至少选择一个选题候选", "danger");
        return false;
      }
      const items = drafts.map((draft, index) => createContentItem({
        accountId: activeAccountId,
        angle: draft.angle,
        audience: draft.audience,
        id: `${activeAccountId}-content-${now}-${index}`,
        pillar: draft.pillar,
        sourceLabel: draft.sourceLabel,
        sourceType: draft.sourceType || "ai_suggestion",
        tags: draft.tags || [],
        targetDuration: draft.targetDuration || 45,
        title: draft.title,
      }));
      updateActiveWorkflow((current) => ({ ...current, contentItems: [...items, ...current.contentItems], selectedContentItemId: items[0].id, selectedSceneId: null }));
      prototypeLogger.info("选题已创建", { accountId: activeAccountId, count: items.length, source: topicDialog.source });
      closeTopicDialog();
      navigate("scripts");
      notify(items.length > 1 ? `已创建 ${items.length} 个独立选题，第一条已打开` : "选题已建立，可以生成第一版脚本");
      return true;
    } catch (error) {
      prototypeLogger.error("创建选题失败", { accountId: activeAccountId, error });
      setTopicDialog((current) => ({ ...current, submitting: false }));
      notify("选题创建失败，请重试并查看日志", "danger");
      return false;
    }
  }

  function createContentItemFromDraft(draft) {
    const item = createContentItem({ ...draft, accountId: activeAccountId, id: draft.id || `${activeAccountId}-content-${Date.now()}` });
    updateActiveWorkflow((current) => ({ ...current, contentItems: [item, ...current.contentItems], selectedContentItemId: item.id, selectedSceneId: null }));
    navigate("scripts");
    return item;
  }

  function updateScript(scriptId, updater) {
    updateActiveWorkflow((current) => ({ ...current, scripts: current.scripts.map((script) => script.id === scriptId ? updater(script) : script) }));
  }

  function updateContentItem(contentItemId, updater) {
    updateActiveWorkflow((current) => ({ ...current, contentItems: current.contentItems.map((item) => item.id === contentItemId ? updater(item) : item) }));
  }

  function saveScript(scriptId, raw) {
    try {
      updateScript(scriptId, (script) => {
        const revision = script.revision + 1;
        return { ...script, adoptedRevision: null, raw, revision, status: "draft", updated: "刚刚", versions: [{ id: `${script.id}-v${revision}`, label: `v${revision}`, source: "人工编辑", status: "review", note: "尚未采用" }, ...script.versions] };
      });
      updateContentItem(selectedContentItem.id, (item) => ({ ...item, stage: "script_draft", updatedAt: "刚刚" }));
      prototypeLogger.info("脚本修改已保存", { accountId: activeAccountId, scriptId });
      notify("脚本已保存，需要重新采用后才能同步分镜", "info");
    } catch (error) {
      prototypeLogger.error("保存脚本失败", { accountId: activeAccountId, error, scriptId });
      notify("脚本保存失败，请重试", "danger");
    }
  }

  function setScriptDraftRaw(raw) {
    setScriptDraft((current) => ({ ...current, raw }));
  }

  function discardScriptDraft() {
    setScriptDraft({ raw: selectedScript?.raw || "", scriptId: selectedScript?.id || null });
  }

  function saveScriptDraft() {
    if (!selectedScript || scriptDraft.scriptId !== selectedScript.id || scriptDraft.raw === selectedScript.raw) return true;
    saveScript(selectedScript.id, scriptDraft.raw);
    setScriptDraft({ raw: scriptDraft.raw, scriptId: selectedScript.id });
    return true;
  }

  async function generateScript(scriptId = selectedScript?.id) {
    try {
      if (!selectedContentItem) return false;
      if (scriptId) updateScript(scriptId, (script) => ({ ...script, status: "running" }));
      notify(scriptId ? "AI 正在按当前账号定位优化脚本" : "AI 正在生成第一版脚本", "info");
      await delay();
      if (!scriptId) {
        const id = `${selectedContentItem.id}-script`;
        const script = buildGeneratedScript(selectedContentItem, id);
        updateActiveWorkflow((current) => ({ ...current, scripts: [script, ...current.scripts], contentItems: current.contentItems.map((item) => item.id === selectedContentItem.id ? { ...item, stage: "script_draft", scriptVersionIds: [`${id}-v1`, ...item.scriptVersionIds] } : item) }));
      } else {
        updateScript(scriptId, (script) => {
          const revision = script.revision + 1;
          return { ...script, adoptedRevision: null, raw: `${script.raw}\n\nAI 建议：开场先展示最终画面，并把每一步压缩为一个可验证动作。`, revision, status: "draft", updated: "刚刚", versions: [{ id: `${script.id}-v${revision}`, label: `v${revision}`, source: "AI 优化", status: "review", note: "等待人工采用" }, ...script.versions] };
        });
        updateContentItem(selectedContentItem.id, (item) => ({ ...item, stage: "script_draft" }));
      }
      notify("AI 脚本版本已生成，请确认采用");
      return true;
    } catch (error) {
      prototypeLogger.error("生成脚本失败", { accountId: activeAccountId, error, scriptId });
      if (scriptId) updateScript(scriptId, (script) => ({ ...script, status: "failed" }));
      notify("AI 脚本生成失败，可重试并查看日志", "danger");
      return false;
    }
  }

  function adoptScript(scriptId) {
    try {
      const script = workflow.scripts.find((item) => item.id === scriptId);
      if (!script) return;
      updateScript(scriptId, (current) => ({ ...current, adoptedRevision: current.revision, status: "adopted", versions: current.versions.map((version, index) => ({ ...version, status: index === 0 ? "adopted" : "history" })) }));
      updateContentItem(script.contentItemId, (item) => ({ ...item, adoptedScriptVersionId: `${script.id}-v${script.revision}`, scriptVersionIds: [...new Set([`${script.id}-v${script.revision}`, ...item.scriptVersionIds])], stage: "script_adopted" }));
      prototypeLogger.info("脚本版本已采用", { accountId: activeAccountId, scriptId });
      notify("脚本已采用，可以进入分镜规划");
    } catch (error) {
      prototypeLogger.error("采用脚本失败", { accountId: activeAccountId, error, scriptId });
      notify("脚本采用失败，请重试", "danger");
    }
  }

  function enterStoryboard(script = selectedScript) {
    if (!canEnterStoryboard(script)) {
      notify("请先采用当前脚本版本，再进入分镜规划", "danger");
      return false;
    }
    navigate("storyboard");
    return true;
  }

  async function generateStoryboard(script = selectedScript) {
    if (!canEnterStoryboard(script)) {
      notify("当前脚本尚未采用，无法生成分镜", "danger");
      return false;
    }
    try {
      notify("AI 正在生成镜头规划", "info");
      await delay();
      const board = buildGeneratedStoryboard(script, `${script.contentItemId}-board-${Date.now()}`);
      updateActiveWorkflow((current) => ({
        ...current,
        contentItems: current.contentItems.map((item) => item.id === script.contentItemId ? { ...item, stage: "storyboard_draft", storyboardVersionIds: [`${board.id}-v1`, ...item.storyboardVersionIds] } : item),
        selectedSceneId: board.scenes[0]?.id || null,
        storyboards: [board, ...current.storyboards.filter((item) => item.contentItemId !== script.contentItemId)],
      }));
      notify("分镜规划已生成，请逐镜确认");
      return true;
    } catch (error) {
      prototypeLogger.error("生成分镜失败", { accountId: activeAccountId, error, scriptId: script.id });
      notify("分镜生成失败，请重试", "danger");
      return false;
    }
  }

  async function retryScene(sceneId) {
    if (!selectedStoryboard) return false;
    const boardId = selectedStoryboard.id;
    try {
      updateBoard(boardId, (board) => updateStoryboardScene(board, sceneId, (scene) => ({ ...scene, error: null, status: "running" })));
      notify("问题镜头已局部重试", "info");
      await delay();
      updateBoard(boardId, (board) => updateStoryboardScene(board, sceneId, (scene) => ({ ...scene, shot: `${scene.shot} · 已重试`, status: "ready" })));
      notify("镜头已恢复，不影响其他分镜");
      return true;
    } catch (error) {
      prototypeLogger.error("分镜局部重试失败", { accountId: activeAccountId, error, sceneId });
      notify("镜头重试失败，请查看日志", "danger");
      return false;
    }
  }

  function confirmStoryboard() {
    if (!canConfirmStoryboard(selectedStoryboard)) {
      notify("请先处理异常镜头，再确认分镜", "danger");
      return false;
    }
    try {
      const versionId = `${selectedStoryboard.id}-v${selectedStoryboard.revision}`;
      updateBoard(selectedStoryboard.id, (board) => ({ ...board, status: "confirmed" }));
      updateContentItem(selectedContentItem.id, (item) => ({ ...item, confirmedStoryboardVersionId: versionId, stage: "storyboard_confirmed", storyboardVersionIds: [...new Set([versionId, ...item.storyboardVersionIds])] }));
      prototypeLogger.info("分镜版本已确认", { accountId: activeAccountId, storyboardId: selectedStoryboard.id });
      notify("分镜已确认，可以进入生产");
      return true;
    } catch (error) {
      prototypeLogger.error("确认分镜失败", { accountId: activeAccountId, error, storyboardId: selectedStoryboard.id });
      notify("分镜确认失败，请重试", "danger");
      return false;
    }
  }

  function updateBoard(boardId, updater) {
    updateActiveWorkflow((current) => ({ ...current, storyboards: current.storyboards.map((board) => board.id === boardId ? updater(board) : board) }));
  }

  return {
    adoptScript,
    closeTopicDialog,
    confirmStoryboard,
    contentItems: workflow.contentItems,
    contentStageLabels,
    createContentItemFromDraft,
    discardScriptDraft,
    enterStoryboard,
    generateScript,
    generateStoryboard,
    generateTopicSuggestions,
    openTopicDialog,
    retryScene,
    saveScriptDraft,
    saveScript,
    selectContentItem,
    selectScene: (id) => updateActiveWorkflow((current) => ({ ...current, selectedSceneId: id })),
    selectedContentItem,
    selectedScene,
    selectedScript,
    selectedStoryboard,
    scriptDraft,
    scriptDraftDirty: Boolean(selectedScript && scriptDraft.scriptId === selectedScript.id && scriptDraft.raw !== selectedScript.raw),
    setScriptDraftRaw,
    setTopicDialogField,
    setTopicSource,
    stages,
    submitTopicDialog,
    toggleTopicSuggestion,
    topicDialog,
  };
}

function buildSuggestions(accountId) {
  if (accountId === "focus") {
    return [
      { id: "focus-ai-1", title: "A calmer weekly desktop reset", pillar: "Weekly reset", angle: "Start from the finished desktop", audience: "Makers", targetDuration: 45, sourceLabel: "Account positioning", sourceType: "ai_suggestion", tags: ["weekly reset"] },
      { id: "focus-ai-2", title: "One screen, one decision", pillar: "Deep work", angle: "Remove one distracting workspace", audience: "Knowledge workers", targetDuration: 30, sourceLabel: "Account positioning", sourceType: "ai_suggestion", tags: ["deep work"] },
      { id: "focus-ai-3", title: "Three quiet file naming rules", pillar: "Desk systems", angle: "Show a before-and-after folder", audience: "Makers", targetDuration: 45, sourceLabel: "Knowledge snapshot", sourceType: "ai_suggestion", tags: ["files"] },
    ];
  }
  return [
    { id: "mirror-ai-1", title: "AI 工具为什么越用越乱", pillar: "工具拆解", angle: "从错误工作流反推三个边界", audience: "AI 工具使用者", targetDuration: 45, sourceLabel: "账号定位 v4", sourceType: "ai_suggestion", tags: ["AI 工具", "工作流"] },
    { id: "mirror-ai-2", title: "一条内容如何进入批量生产", pillar: "效率实验", angle: "对比单条生产和单项批次", audience: "内容创作者", targetDuration: 60, sourceLabel: "知识快照 · 演示", sourceType: "ai_suggestion", tags: ["批量生产"] },
    { id: "mirror-ai-3", title: "账号知识库不串号的三个条件", pillar: "真实复盘", angle: "用账号切换演示隔离验证", audience: "多账号运营者", targetDuration: 45, sourceLabel: "账号定位 v4", sourceType: "ai_suggestion", tags: ["知识库", "账号隔离"] },
  ];
}

function delay() {
  return new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
}
