import { IconAlertCircle, IconSearch } from "@tabler/icons-react";
import { AccountDetailDrawer } from "../components/account-management/AccountDetailDrawer.jsx";
import { AccountTable } from "../components/account-management/AccountTable.jsx";
import { AccountWizard } from "../components/account-wizard/AccountWizard.jsx";

const filters = [
  ["all", "全部"],
  ["ready", "可用"],
  ["attention", "需处理"],
  ["draft", "草稿"],
  ["archived", "已归档"],
];

export function AccountManagement({ state }) {
  const manager = state.accountManagement;
  const source = manager.profiles.find((profile) => profile.id === manager.wizard.sourceId) || null;

  function complete(form) {
    const profile = manager.completeAccount(form);
    if (profile?.status === "ready") state.registerAccountWorkspace(profile);
  }

  return (
    <div className="page-stack account-management-page page-enter">
      <div className="account-toolbar">
        <label className="account-management-search"><IconSearch size={16} /><input value={manager.query} onChange={(event) => manager.setQuery(event.target.value)} placeholder="搜索账号、平台或定位" /></label>
        <div className="filter-tabs" role="tablist">{filters.map(([id, label]) => <button className={manager.statusFilter === id ? "is-active" : ""} key={id} onClick={() => manager.setStatusFilter(id)} role="tab" type="button">{label}</button>)}</div>
      </div>
      <section className="page-section account-list-section">
        <div className="page-section__header"><div><h2>账号工作区</h2><p>每个账号拥有独立定位、知识、AI 配方和生产内容</p></div><span className="demo-chip">{manager.filteredProfiles.length} 个演示账号</span></div>
        <AccountTable
          activeAccountId={state.activeAccountId}
          onArchive={manager.archiveProfile}
          onCopy={manager.copyProfile}
          onOpen={manager.setSelectedAccountId}
          onRestore={manager.restoreProfile}
          onSwitch={state.switchAccount}
          profiles={manager.filteredProfiles}
        />
      </section>
      <div className="account-boundary-note"><IconAlertCircle size={17} /><span><strong>系统级账号管理</strong><small>这里不展示粉丝、收益或经营指标；授权与设备绑定均为演示状态。</small></span></div>
      <AccountDetailDrawer
        account={manager.selectedAccount}
        onArchive={manager.archiveProfile}
        onClose={() => manager.setSelectedAccountId(null)}
        onCopy={manager.copyProfile}
        onRestore={manager.restoreProfile}
        onUpdateRecipe={manager.updateRecipe}
      />
      <AccountWizard
        key={`${manager.wizard.open}-${manager.wizard.sourceId || "new"}`}
        onClose={manager.closeWizard}
        onComplete={complete}
        onSaveDraft={manager.saveDraft}
        open={manager.wizard.open}
        source={source}
      />
    </div>
  );
}
