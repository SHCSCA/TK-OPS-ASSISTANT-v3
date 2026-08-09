import { IconPlus, IconRefresh } from "@tabler/icons-react";
import { PageSection } from "../components/PageSection.jsx";
import { ApplyResultPreviewDialog } from "../components/video-deconstruction/ApplyResultPreviewDialog.jsx";
import { DeconstructionList } from "../components/video-deconstruction/DeconstructionList.jsx";
import { DeconstructionResult } from "../components/video-deconstruction/DeconstructionResult.jsx";
import { DeconstructionStages } from "../components/video-deconstruction/DeconstructionStages.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function VideoDeconstruction({ state }) {
  const creative = state.creative;
  const item = creative.deconstruction.selectedDeconstruction;
  const route = state.aiSettings.routeStatuses.deconstruction;
  const emptyState = resolvePageEmptyState("deconstruction", state.dataScenario, creative.workflow.deconstructions.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.notify("已打开媒体选择器 · 演示", "info")} /></div>;
  const deconstructionAction = route.ready ? () => state.notify("已打开媒体选择器 · 演示", "info") : () => { state.navigate("settings"); state.notify(`拆解能力不可用：${route.reason}`, "danger"); };
  return <div className="page-stack page-enter"><PageSection title="视频拆解" meta="拆解是创作来源，可回流到选题、脚本、分镜与知识" action={<button className="secondary-button" onClick={deconstructionAction} type="button"><IconPlus size={16} />{route.ready ? "新建拆解" : "配置拆解能力"}</button>}><div className="creative-workspace creative-workspace--deconstruction"><DeconstructionList creative={creative} /><section className="workflow-main">{item ? <><header className="workspace-card-header"><div><span className="section-kicker">{item.source}</span><h2>{item.title}</h2></div><span className={`status-pill status-pill--${item.status === "completed" ? "ready" : item.status === "running" ? "ai" : "danger"}`}>{item.status === "completed" ? "结果就绪" : item.status === "running" ? "处理中" : "失败"}</span></header><DeconstructionStages stages={item.stages} /><DeconstructionResult item={item} onApply={creative.deconstruction.openApplyDialog} onEvidence={(keyword, time) => state.notify(`已定位 ${keyword} 的证据时间 ${time}`, "info")} onRetry={() => state.notify("关键帧提取已重新排队", "info")} />{item.status === "failed" ? <button className="primary-button recovery-action" onClick={() => creative.deconstruction.retryDeconstruction(item.id)} type="button"><IconRefresh size={16} />从失败阶段继续</button> : null}</> : <div className="empty-workflow"><strong>暂无拆解任务</strong><span>导入已授权视频后开始分析。</span></div>}</section></div></PageSection><ApplyResultPreviewDialog creative={creative} /></div>;
}
