import { IconCheck, IconChevronUp, IconPlus, IconSearch, IconSettings } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { AccountAvatar } from "./AccountAvatar.jsx";

export function AccountSwitcher({ accounts, activeAccount, open, onAddAccount, onManageAccounts, onOpenChange, onSwitch }) {
  const [query, setQuery] = useState("");
  const filteredAccounts = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return accounts;
    return accounts.filter((account) =>
      `${account.name} ${account.positioning}`.toLowerCase().includes(normalized),
    );
  }, [accounts, query]);

  return (
    <div className="account-switcher">
      {open ? (
        <div className="account-menu" role="dialog" aria-label="切换账号">
          <div className="account-menu__header">
            <span>切换账号</span>
            <span className="demo-chip">演示</span>
          </div>
          <label className="account-search">
            <IconSearch size={16} stroke={1.8} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索账号或定位"
              autoFocus
            />
          </label>
          <div className="account-menu__list">
            {filteredAccounts.map((account) => (
              <button
                className={`account-option ${account.status !== "ready" ? "is-disabled" : ""}`}
                disabled={account.status !== "ready"}
                key={account.id}
                onClick={() => onSwitch(account.id)}
                type="button"
              >
                <AccountAvatar account={account} size="sm" />
                <span className="account-option__copy">
                  <strong>{account.name}</strong>
                  <small>{account.shortPositioning || account.positioning}{account.status !== "ready" ? ` · ${account.status === "archived" ? "已归档" : "待配置"}` : ""}</small>
                </span>
                {account.id === activeAccount.id ? <IconCheck size={17} stroke={2} /> : null}
              </button>
            ))}
            {filteredAccounts.length === 0 ? <div className="account-menu__empty">没有匹配账号</div> : null}
          </div>
          <div className="account-menu__footer">
            <button onClick={onAddAccount} type="button"><IconPlus size={16} />添加账号</button>
            <button onClick={onManageAccounts} type="button"><IconSettings size={16} />管理账号</button>
          </div>
        </div>
      ) : null}
      <button
        aria-label={`切换账号：${activeAccount.name}`}
        className="account-switcher__button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => onOpenChange(!open)}
        type="button"
      >
        <AccountAvatar account={activeAccount} />
        <span className="account-switcher__copy">
          <strong>{activeAccount.name}</strong>
          <small>{activeAccount.platform} · {activeAccount.positioning}</small>
        </span>
        <IconChevronUp className="account-switcher__chevron" size={17} stroke={1.8} />
      </button>
    </div>
  );
}
