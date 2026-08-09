import { IconAlertTriangle, IconArrowRight, IconCheck, IconClock, IconLoader2, IconRefresh } from "@tabler/icons-react";
import { getEntryReadiness } from "../../data/productionBatches.js";

const icons = { blocked: IconAlertTriangle, completed: IconCheck, failed: IconAlertTriangle, queued: IconClock, review: IconClock, running: IconLoader2 };

export function BatchEntryTable({ creative, entries, onClearFilter, onOpen }) {
  if (!entries.length) return <div className="table-empty">当前批次没有符合筛选条件的内容{onClearFilter ? <button className="text-action" onClick={onClearFilter} type="button">清除筛选</button> : null}</div>;
  return (
    <div className="batch-entry-table" role="table" aria-label="批次内容队列">
      <div className="batch-entry-head" role="row"><span>内容</span><span>选题</span><span>脚本</span><span>分镜</span><span>生产</span><span>输出</span><span /></div>
      {entries.map((entry) => {
        const item = creative.contentItems.find((candidate) => candidate.id === entry.contentItemId);
        const script = creative.workflow.scripts.find((candidate) => candidate.contentItemId === entry.contentItemId);
        const board = creative.workflow.storyboards.find((candidate) => candidate.contentItemId === entry.contentItemId);
        const readiness = getEntryReadiness(entry, item, script, board);
        const StatusIcon = icons[entry.status] || IconClock;
        return (
          <button className={`batch-entry-row ${entry.blocker ? "is-blocked" : ""}`} key={entry.id} onClick={() => onOpen(entry)} role="row" type="button">
            <span className="batch-entry-title"><StatusIcon className={entry.status === "running" ? "spin" : ""} size={16} /><span><strong>{entry.title}</strong><small>{entry.sourceMode === "confirmed" ? "已确认内容" : "批次内创建"}</small></span></span>
            <StageValue label={readiness.topic} />
            <StageValue label={readiness.script} tone={readiness.script.includes("待") || readiness.script === "缺失" ? "warning" : "ready"} />
            <StageValue label={readiness.storyboard} tone={readiness.storyboard.includes("异常") || readiness.storyboard === "缺失" ? "danger" : readiness.storyboard.includes("待") ? "warning" : "ready"} />
            <StageValue label={readiness.production} tone={entry.blocker || entry.status === "failed" ? "danger" : entry.status === "completed" ? "ready" : "active"} />
            <StageValue label={readiness.output} tone={entry.outputAssetIds.length ? "ready" : "muted"} />
            <IconArrowRight className="batch-entry-open" size={16} />
          </button>
        );
      })}
    </div>
  );
}

function StageValue({ label, tone = "muted" }) {
  return <span className={`batch-stage-value batch-stage-value--${tone}`}>{label}</span>;
}
