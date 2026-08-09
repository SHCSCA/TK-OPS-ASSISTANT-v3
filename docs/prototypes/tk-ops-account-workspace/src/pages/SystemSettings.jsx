import { IconActivityHeartbeat, IconFileText, IconMoon, IconRefresh, IconSparkles, IconSun } from "@tabler/icons-react";
import { useState } from "react";
import { AICapabilitiesCenter } from "../components/ai-capabilities/AICapabilitiesCenter.jsx";
import { PageSection } from "../components/PageSection.jsx";

const states = [["ready", "正常"], ["loading", "加载"], ["error", "错误"]];
const tabs = [["ai", "AI 能力", IconSparkles], ["runtime", "Runtime 与工作区", IconActivityHeartbeat], ["logs", "日志与诊断", IconFileText]];

function RuntimeSettings({ state }) {
  return <div className="page-stack"><PageSection title="主题" meta="Light / Dark 使用同一结构和语义"><div className="setting-choice-row"><button className={state.theme === "light" ? "is-active" : ""} onClick={() => state.setTheme("light")} type="button"><IconSun size={18} />浅色</button><button className={state.theme === "dark" ? "is-active" : ""} onClick={() => state.setTheme("dark")} type="button"><IconMoon size={18} />深色</button></div></PageSection><PageSection title="原型请求状态" meta="加载与错误由统一状态层覆盖"><div className="setting-choice-row">{states.map(([id, label]) => <button className={state.pageState === id ? "is-active" : ""} key={id} onClick={() => state.setPageState(id)} type="button"><IconActivityHeartbeat size={18} />{label}</button>)}</div></PageSection><PageSection title="账号数据场景" meta="零数据使用各页面真实空态，不再全屏覆盖"><div className="setting-choice-row"><button className={state.dataScenario === "seeded" ? "is-active" : ""} onClick={() => state.setDataScenario("seeded")} type="button">有数据</button><button className={state.dataScenario === "empty" ? "is-active" : ""} onClick={() => state.setDataScenario("empty")} type="button">零数据</button></div></PageSection><PageSection title="配置总线" meta="本地原型不连接生产服务"><div className="system-list"><span><strong>Prototype Runtime</strong><small>状态与任务仅在浏览器内演示</small><i className="status-pill status-pill--ready">正常</i></span><span><strong>账号配置覆盖</strong><small>定位、知识和 AI Recipe 按账号隔离</small><i className="status-pill status-pill--brand">已隔离</i></span></div></PageSection></div>;
}

function LogsPanel({ state }) {
  return <div className="page-stack"><PageSection title="日志与诊断" meta="异常转换为中文反馈，技术详情默认折叠"><div className="system-list"><span><strong>账号切换日志</strong><small>最近一次演示切换已记录</small><button className="text-action" onClick={() => state.notify("已打开账号切换日志", "info")} type="button"><IconRefresh size={15} />查看</button></span><span><strong>AI 任务日志</strong><small>按 Provider、模型、账号与批次追踪</small><button className="text-action" onClick={() => state.notify("已打开 AI 任务日志", "info")} type="button"><IconRefresh size={15} />查看</button></span><span><strong>Runtime 诊断</strong><small>本地交互原型，不执行真实检测</small><button className="text-action" onClick={() => state.notify("演示诊断完成", "info")} type="button"><IconActivityHeartbeat size={15} />演示检测</button></span></div></PageSection></div>;
}

export function SystemSettings({ state }) {
  const [tab, setTab] = useState("ai");
  return <div className="settings-layout page-enter"><nav className="settings-tabs" aria-label="系统设置分区">{tabs.map(([id, label, Icon]) => <button className={tab === id ? "is-active" : ""} key={id} onClick={() => setTab(id)} type="button"><Icon size={17} />{label}</button>)}</nav><div className="settings-content">{tab === "ai" ? <AICapabilitiesCenter state={state} /> : tab === "runtime" ? <RuntimeSettings state={state} /> : <LogsPanel state={state} />}</div></div>;
}
