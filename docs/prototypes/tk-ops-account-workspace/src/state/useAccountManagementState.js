import { useMemo, useState } from "react";
import { cloneAccountProfiles, createCopiedDraft } from "../data/accountManagement.js";
import { prototypeLogger } from "../utils/logger.js";

export function useAccountManagementState(notify) {
  const [profiles, setProfiles] = useState(cloneAccountProfiles);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [wizard, setWizard] = useState({ open: false, sourceId: null });

  const filteredProfiles = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return profiles.filter((profile) => {
      const matchesText = !normalized || `${profile.name} ${profile.positioning} ${profile.platform}`.toLowerCase().includes(normalized);
      const matchesStatus = statusFilter === "all" || statusFilter === profile.status || (statusFilter === "attention" && ["attention", "unbound"].includes(profile.status));
      return matchesText && matchesStatus;
    });
  }, [profiles, query, statusFilter]);

  const selectedAccount = profiles.find((profile) => profile.id === selectedAccountId) || null;

  function openWizard(sourceId = null) {
    setWizard({ open: true, sourceId });
  }

  function closeWizard() {
    setWizard({ open: false, sourceId: null });
  }

  function saveDraft(form) {
    try {
      const id = form.id || `draft-${Date.now()}`;
      const draft = {
        id,
        initials: (form.name || "新").slice(0, 1),
        name: form.name || "未命名账号",
        platform: "TikTok",
        positioning: form.positioning || "定位信息尚未完成",
        shortPositioning: form.shortPositioning || "待配置",
        status: "draft",
        recent: "刚刚",
        readiness: { connection: form.connectionState === "passed" ? "ready" : "idle", knowledge: form.knowledgeReady ? "ready" : "idle", ai: form.recipeId ? "ready" : "idle" },
        connection: form.connection || {},
        recipe: form.recipe || null,
      };
      setProfiles((current) => [draft, ...current.filter((item) => item.id !== id)]);
      prototypeLogger.info("账号草稿已保存", { accountId: id });
      notify("账号草稿已保存");
      closeWizard();
      return draft;
    } catch (error) {
      prototypeLogger.error("保存账号草稿失败", error);
      notify("保存草稿失败，请重试", "danger");
      return null;
    }
  }

  function completeAccount(form) {
    try {
      const profile = {
        id: form.id || `account-${Date.now()}`,
        initials: (form.name || "新").slice(0, 1),
        name: form.name.trim(),
        platform: "TikTok",
        positioning: form.positioning,
        shortPositioning: form.shortPositioning || form.positioning.slice(0, 12),
        status: form.connectionState === "passed" && form.knowledgeReady && form.recipe ? "ready" : "unbound",
        recent: "刚刚",
        readiness: { connection: form.connectionState === "passed" ? "ready" : "warning", knowledge: form.knowledgeReady ? "ready" : "warning", ai: form.recipe ? "ready" : "warning" },
        connection: form.connection || {},
        recipe: form.recipe,
      };
      setProfiles((current) => [profile, ...current.filter((item) => item.id !== profile.id)]);
      setSelectedAccountId(profile.id);
      closeWizard();
      prototypeLogger.info("演示账号已创建", { accountId: profile.id, status: profile.status });
      notify(profile.status === "ready" ? "账号已创建，可切换到新工作区" : "账号已保存，请先完成连接", profile.status === "ready" ? "success" : "info");
      return profile;
    } catch (error) {
      prototypeLogger.error("创建账号失败", error);
      notify("创建账号失败，请检查后重试", "danger");
      return null;
    }
  }

  function copyProfile(accountId) {
    try {
      const source = profiles.find((profile) => profile.id === accountId);
      if (!source) throw new Error("未找到源账号");
      const copied = createCopiedDraft(source, `copy-${Date.now()}`);
      setProfiles((current) => [copied, ...current]);
      setSelectedAccountId(copied.id);
      openWizard(source.id);
      prototypeLogger.info("账号配置已复制为草稿", { sourceId: accountId, targetId: copied.id });
      notify("已复制配置白名单，授权与内容未复制");
      return copied;
    } catch (error) {
      prototypeLogger.error("复制账号配置失败", error);
      notify("复制配置失败，请重试", "danger");
      return null;
    }
  }

  function archiveProfile(accountId) {
    setProfiles((current) => current.map((profile) => profile.id === accountId ? { ...profile, status: "archived", recent: "刚刚" } : profile));
    prototypeLogger.info("账号已归档", { accountId });
    notify("账号已归档，数据仍保留");
  }

  function restoreProfile(accountId) {
    setProfiles((current) => current.map((profile) => profile.id === accountId ? { ...profile, status: "attention", recent: "刚刚" } : profile));
    prototypeLogger.info("账号已恢复并等待健康检查", { accountId });
    notify("账号已恢复，请完成健康检查", "info");
  }

  function updateRecipe(accountId, recipe) {
    setProfiles((current) => current.map((profile) => profile.id === accountId ? { ...profile, recipe, readiness: { ...profile.readiness, ai: "ready" } } : profile));
    prototypeLogger.info("账号 AI 创作档案已更新", { accountId, recipeId: recipe?.id });
    notify("账号 AI 创作档案已更新");
  }

  return {
    archiveProfile,
    closeWizard,
    completeAccount,
    copyProfile,
    filteredProfiles,
    openWizard,
    profiles,
    query,
    restoreProfile,
    saveDraft,
    selectedAccount,
    selectedAccountId,
    setQuery,
    setSelectedAccountId,
    setStatusFilter,
    statusFilter,
    updateRecipe,
    wizard,
  };
}
