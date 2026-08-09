import { IconAlertCircle, IconInbox, IconLoader2, IconRefresh } from "@tabler/icons-react";

export function StatePanel({ state, onRetry }) {
  if (state === "loading") {
    return <div className="state-panel"><IconLoader2 className="spin" size={24} /><h2>正在加载当前账号</h2><p>定位、批次和任务正在同步。</p></div>;
  }
  if (state === "empty") {
    return <div className="state-panel"><IconInbox size={26} /><h2>这个账号还没有内容</h2><p>创建第一个批次即可开始。</p><button className="primary-button" onClick={onRetry} type="button">创建批次</button></div>;
  }
  if (state === "error") {
    return <div className="state-panel state-panel--error"><IconAlertCircle size={26} /><h2>账号数据加载失败</h2><p>演示错误已被记录，重试后恢复工作区。</p><button className="secondary-button" onClick={onRetry} type="button"><IconRefresh size={16} />重试加载</button></div>;
  }
  return null;
}
