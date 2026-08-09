import { useEffect, useState } from "react";
import { AppSidebar } from "./components/AppSidebar.jsx";
import { DetailPanel } from "./components/DetailPanel.jsx";
import { BatchWizard } from "./components/batch-wizard/BatchWizard.jsx";
import { StatePanel } from "./components/StatePanel.jsx";
import { ToastRegion } from "./components/ToastRegion.jsx";
import { TopBar } from "./components/TopBar.jsx";
import { UnsavedChangesDialog } from "./components/UnsavedChangesDialog.jsx";
import { BatchProduction } from "./pages/BatchProduction.jsx";
import { ContentLibrary } from "./pages/ContentLibrary.jsx";
import { MediaToolbox } from "./pages/MediaToolbox.jsx";
import { Publishing } from "./pages/Publishing.jsx";
import { Review } from "./pages/Review.jsx";
import { ScriptTopicCenter } from "./pages/ScriptTopicCenter.jsx";
import { StrategyKnowledge } from "./pages/StrategyKnowledge.jsx";
import { StoryboardPlanning } from "./pages/StoryboardPlanning.jsx";
import { SystemSettings } from "./pages/SystemSettings.jsx";
import { VideoDeconstruction } from "./pages/VideoDeconstruction.jsx";
import { WorkspaceHome } from "./pages/WorkspaceHome.jsx";
import { AccountManagement } from "./pages/AccountManagement.jsx";
import { useAccountManagementState } from "./state/useAccountManagementState.js";
import { useAISettingsState } from "./state/useAISettingsState.js";
import { useCreativeWorkflowState } from "./state/useCreativeWorkflowState.js";
import { useMediaToolsState } from "./state/useMediaToolsState.js";
import { useWorkspaceState } from "./state/useWorkspaceState.js";

const pages = {
  accounts: AccountManagement,
  deconstruction: VideoDeconstruction,
  knowledge: StrategyKnowledge,
  library: ContentLibrary,
  scripts: ScriptTopicCenter,
  storyboard: StoryboardPlanning,
  production: BatchProduction,
  publishing: Publishing,
  review: Review,
  settings: SystemSettings,
  toolbox: MediaToolbox,
  workspace: WorkspaceHome,
};

export function App() {
  const workspaceState = useWorkspaceState();
  const accountManagement = useAccountManagementState(workspaceState.notify);
  const aiSettings = useAISettingsState(workspaceState.notify);
  const creative = useCreativeWorkflowState(workspaceState.activeAccountId, workspaceState.notify, workspaceState.navigate);
  const media = useMediaToolsState(workspaceState.activeAccountId, workspaceState.notify);
  const [pendingAccountId, setPendingAccountId] = useState(null);
  const state = { ...workspaceState, accountManagement, aiSettings, creative, media, switchAccount: requestAccountSwitch };
  const ActivePage = pages[state.activePage] || WorkspaceHome;
  const showPageState = !["accounts", "settings"].includes(state.activePage) && ["loading", "error"].includes(state.pageState);
  const activeAccountProfile = accountManagement.profiles.find((profile) => profile.id === state.activeAccountId) || null;

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        if (pendingAccountId) {
          setPendingAccountId(null);
          return;
        }
        state.setAccountMenuOpen(false);
        state.setBatchDialogOpen(false);
        state.setDetail(null);
        accountManagement.closeWizard();
        accountManagement.setSelectedAccountId(null);
        aiSettings.setSelectedProviderId(null);
        creative.closeTopicDialog();
        creative.production.closeHandoff();
        creative.deconstruction.closeApplyDialog();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "n" && !["accounts", "settings"].includes(state.activePage)) {
        event.preventDefault();
        if (state.activePage === "scripts") creative.openTopicDialog();
        else state.setBatchDialogOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [state]);

  async function requestAccountSwitch(accountId) {
    if (creative.scriptDraftDirty) {
      workspaceState.setAccountMenuOpen(false);
      setPendingAccountId(accountId);
      return false;
    }
    await workspaceState.switchAccount(accountId);
    return true;
  }

  async function resolveAccountSwitch(saveDraft) {
    const accountId = pendingAccountId;
    if (!accountId) return;
    if (saveDraft) creative.saveScriptDraft();
    else creative.discardScriptDraft();
    setPendingAccountId(null);
    await workspaceState.switchAccount(accountId);
  }

  function recoverPage() {
    state.setPageState("loading");
    window.setTimeout(() => {
      state.setPageState("ready");
      state.notify("当前账号已恢复");
    }, 650);
  }

  async function createBatch(form) {
    const result = await creative.production.createGenericBatch(form);
    if (result) state.setBatchDialogOpen(false);
    return Boolean(result);
  }

  return (
    <div className="app-shell">
      <AppSidebar state={state} />
      <div className="app-main">
        <TopBar state={state} />
        <main className="content-host">
          {showPageState ? <StatePanel state={state.pageState} onRetry={recoverPage} /> : <ActivePage state={state} />}
        </main>
        <footer className="status-bar"><span>Prototype Runtime · 已连接</span><span>演示数据仅用于交互验证</span></footer>
      </div>
      <DetailPanel state={state} />
      <BatchWizard
        accountProfile={activeAccountProfile}
        aiSettings={aiSettings}
        accountName={state.workspace.account.name}
        onClose={() => state.setBatchDialogOpen(false)}
        onSubmit={createBatch}
        open={state.batchDialogOpen}
        workspace={state.workspace}
      />
      <UnsavedChangesDialog
        accountName={state.accounts.find((account) => account.id === pendingAccountId)?.name || "目标账号"}
        onCancel={() => setPendingAccountId(null)}
        onDiscard={() => resolveAccountSwitch(false)}
        onSave={() => resolveAccountSwitch(true)}
        open={Boolean(pendingAccountId)}
      />
      {state.switching ? <div className="switching-overlay"><span className="switching-spinner" /><strong>正在切换账号工作区</strong><small>清理旧账号上下文并同步新账号内容</small></div> : null}
      <ToastRegion toast={state.toast} />
    </div>
  );
}
