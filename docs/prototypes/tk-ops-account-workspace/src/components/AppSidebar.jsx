import { Fragment } from "react";
import { IconSettings } from "@tabler/icons-react";
import { navigationItems } from "../data/navigation.js";
import { AccountSwitcher } from "./AccountSwitcher.jsx";
import { Brand } from "./Brand.jsx";

export function AppSidebar({ state }) {
  return (
    <aside className="app-sidebar">
      <Brand />
      <nav className="app-nav" aria-label="账号工作区导航">
        {navigationItems.map((item, index) => {
          const Icon = item.icon;
          const active = state.activePage === item.id;
          const previousGroup = navigationItems[index - 1]?.group;
          const showDivider = item.group && item.group !== previousGroup;
          return (
            <Fragment key={item.id}>
            {showDivider ? <span className="app-nav__divider" aria-hidden="true" /> : null}
            <button
              aria-label={item.label}
              className={`app-nav__item ${active ? "is-active" : ""}`}
              data-tooltip={item.label}
              onClick={() => state.navigate(item.id)}
              type="button"
            >
              <Icon size={19} stroke={1.75} />
              <span>{item.label}</span>
            </button>
            </Fragment>
          );
        })}
      </nav>
      <button
        aria-label="系统设置"
        className={`app-nav__item app-sidebar__settings ${state.activePage === "settings" ? "is-active" : ""}`}
        data-tooltip="系统设置"
        onClick={() => state.navigate("settings")}
        type="button"
      >
        <IconSettings size={19} stroke={1.75} />
        <span>系统设置</span>
      </button>
      <AccountSwitcher
        accounts={state.accountManagement.profiles}
        activeAccount={state.workspace.account}
        open={state.accountMenuOpen}
        onOpenChange={state.setAccountMenuOpen}
        onAddAccount={() => { state.setAccountMenuOpen(false); state.accountManagement.openWizard(); }}
        onManageAccounts={() => state.navigate("accounts")}
        onSwitch={state.switchAccount}
      />
    </aside>
  );
}
