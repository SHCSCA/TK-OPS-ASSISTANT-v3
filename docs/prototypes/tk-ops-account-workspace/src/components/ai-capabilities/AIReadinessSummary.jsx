import { IconAlertTriangle, IconCircleCheck, IconSparkles } from "@tabler/icons-react";

export function AIReadinessSummary({ readyCount, routeCount, providerCount, onAddProvider }) {
  const missingCount = routeCount - readyCount;
  return <div className="ai-summary-bar"><span><IconSparkles size={18} /><small>能力路由</small><strong>{readyCount} / {routeCount} 就绪</strong></span><span><IconCircleCheck size={17} /><small>Provider</small><strong>{providerCount} 个已配置</strong></span><span><IconAlertTriangle size={17} /><small>待补配置</small><strong>{missingCount} 项</strong></span><button className="primary-button" onClick={onAddProvider} type="button">添加 Provider</button></div>;
}
