import { IconMoon, IconPlus, IconSun } from "@tabler/icons-react";
import { navigationItems } from "../data/navigation.js";

const pageTitles = Object.fromEntries(navigationItems.map((item) => [item.id, item.label]));
pageTitles.settings = "系统设置";
pageTitles.accounts = "账号管理";

export function TopBar({ state }) {
  const canCreate = state.dataScenario !== "empty" && ["workspace", "production"].includes(state.activePage);
  const isSystemPage = ["accounts", "settings"].includes(state.activePage);
  return (
    <header className="top-bar">
      <div className="top-bar__title">
        <div className="top-bar__title-row">
          <h1>{pageTitles[state.activePage]}</h1>
          <span className="demo-chip">演示原型</span>
        </div>
        <p>{isSystemPage ? "系统级配置 · 账号工作区保持独立" : `${state.workspace.account.name} · ${state.workspace.account.positioning}`}</p>
      </div>
      <div className="top-bar__actions">
        <span className="health-chip"><i />Runtime 正常</span>
        <button
          className="icon-button theme-button"
          aria-label={state.theme === "light" ? "切换深色主题" : "切换浅色主题"}
          onClick={() => state.setTheme(state.theme === "light" ? "dark" : "light")}
          type="button"
        >
          {state.theme === "light" ? <IconMoon size={18} /> : <IconSun size={18} />}
        </button>
        {canCreate ? (
          <button className="primary-button" onClick={() => state.setBatchDialogOpen(true)} type="button">
            <IconPlus size={18} stroke={2.1} />
            新建批次
          </button>
        ) : state.activePage === "accounts" ? <button className="primary-button" onClick={() => state.accountManagement.openWizard()} type="button"><IconPlus size={18} stroke={2.1} />添加账号</button> : null}
      </div>
    </header>
  );
}
