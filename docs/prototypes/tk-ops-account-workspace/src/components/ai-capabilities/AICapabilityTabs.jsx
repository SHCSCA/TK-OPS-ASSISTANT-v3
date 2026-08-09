import { IconBrain, IconRoute, IconServer } from "@tabler/icons-react";

const tabs = [
  ["providers", "Provider", IconServer],
  ["models", "模型与路由", IconRoute],
  ["prompts", "Prompt", IconBrain],
];

export function AICapabilityTabs({ activeTab, onChange }) {
  return <nav aria-label="AI 配置分区" className="ai-local-tabs">{tabs.map(([id, label, Icon]) => <button aria-current={activeTab === id ? "page" : undefined} className={activeTab === id ? "is-active" : ""} key={id} onClick={() => onChange(id)} type="button"><Icon size={16} />{label}</button>)}</nav>;
}
