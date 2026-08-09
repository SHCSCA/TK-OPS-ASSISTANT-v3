import { IconPlus, IconRefresh } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { BatchEntryTable } from "../components/batch-production/BatchEntryTable.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

const filters = [
  { id: "all", label: "全部" },
  { id: "blocked", label: "异常" },
  { id: "review", label: "待确认" },
  { id: "completed", label: "已完成" },
];

export function BatchProduction({ state }) {
  const creative = state.creative;
  const production = creative.production;
  const [filter, setFilter] = useState("all");
  const entries = useMemo(() => production.batchEntries.filter((entry) => {
    if (filter === "blocked") return Boolean(entry.blocker) || ["blocked", "failed"].includes(entry.status);
    if (filter === "review") return entry.status === "review";
    if (filter === "completed") return entry.status === "completed";
    return true;
  }), [filter, production.batchEntries]);
  const batch = production.selectedBatch;
  const emptyState = resolvePageEmptyState("production", state.dataScenario, production.batches.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.setBatchDialogOpen(true)} /></div>;

  return (
    <div className="page-stack page-enter">
      <section className="batch-hero batch-hero--orchestrator">
        <div className="batch-switcher"><span className="dialog-eyebrow">生产批次</span><select aria-label="切换批次" onChange={(event) => production.selectBatch(event.target.value)} value={batch?.id || ""}>{production.batches.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><p>{batch ? `${batch.stage} · ${batch.items} 条内容 · ${batch.recipe}` : "尚未创建批次"}</p></div>
        <div className="batch-hero__progress"><strong>{batch?.progress || 0}%</strong><span className="progress-track progress-track--large"><i style={{ width: `${batch?.progress || 0}%` }} /></span></div>
        <div className="batch-hero__actions"><button className="secondary-button" onClick={() => state.notify("批次状态已刷新", "info")} type="button"><IconRefresh size={16} />刷新</button><button className="primary-button" onClick={() => state.setBatchDialogOpen(true)} type="button"><IconPlus size={16} />新建批次</button></div>
      </section>
      <section className="section-block batch-orchestrator">
        <header className="section-block__header"><div><h2>内容队列</h2><span>每条内容保留自己的选题、脚本与分镜引用</span></div><div className="filter-tabs" role="tablist">{filters.map((item) => <button aria-selected={filter === item.id} className={filter === item.id ? "is-active" : ""} key={item.id} onClick={() => setFilter(item.id)} role="tab" type="button">{item.label}</button>)}</div></header>
        <BatchEntryTable creative={creative} entries={entries} onClearFilter={filter === "all" ? null : () => setFilter("all")} onOpen={(entry) => state.setDetail({ type: "batch-entry", data: entry })} />
      </section>
    </div>
  );
}
