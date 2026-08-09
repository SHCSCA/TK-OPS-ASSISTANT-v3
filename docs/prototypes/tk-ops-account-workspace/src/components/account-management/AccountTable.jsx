import { IconArchive, IconCopy, IconDots, IconRestore } from "@tabler/icons-react";
import { accountStatusMeta } from "../../data/accountManagement.js";
import { AccountAvatar } from "../AccountAvatar.jsx";
import { ReadinessIndicators } from "./ReadinessIndicators.jsx";

export function AccountTable({ profiles, activeAccountId, onArchive, onCopy, onOpen, onRestore, onSwitch }) {
  if (!profiles.length) return <div className="table-empty">当前筛选下没有账号</div>;
  return (
    <div className="account-table-wrap">
      <table className="account-table">
        <thead><tr><th>账号</th><th>定位</th><th>连接 / 知识 / AI</th><th>最近使用</th><th>动作</th><th aria-label="更多" /></tr></thead>
        <tbody>
          {profiles.map((profile) => {
            const meta = accountStatusMeta[profile.status];
            const canSwitch = profile.status === "ready";
            return (
              <tr className={profile.status === "archived" ? "is-archived" : profile.status === "attention" ? "is-attention" : ""} key={profile.id}>
                <td><button className="account-identity" onClick={() => onOpen(profile.id)} type="button"><AccountAvatar account={profile} size="sm" /><span><strong>{profile.name}</strong><small>{profile.platform} · <i className={`status-dot status-dot--${meta.tone}`} />{meta.label}{profile.id === activeAccountId ? " · 当前" : ""}</small></span></button></td>
                <td><span className="account-positioning">{profile.positioning}</span></td>
                <td><ReadinessIndicators readiness={profile.readiness} /></td>
                <td><span className="account-recent">{profile.recent}</span></td>
                <td><button className={canSwitch ? "text-action" : "secondary-button account-row-action"} onClick={() => canSwitch ? onSwitch(profile.id) : onOpen(profile.id)} type="button">{profile.id === activeAccountId ? "当前账号" : meta.action}</button></td>
                <td>
                  <details className="row-menu"><summary aria-label="更多账号操作"><IconDots size={17} /></summary><div>
                    <button onClick={() => onCopy(profile.id)} type="button"><IconCopy size={15} />复制配置</button>
                    {profile.status === "archived" ? <button onClick={() => onRestore(profile.id)} type="button"><IconRestore size={15} />恢复账号</button> : <button onClick={() => onArchive(profile.id)} type="button"><IconArchive size={15} />归档账号</button>}
                  </div></details>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
