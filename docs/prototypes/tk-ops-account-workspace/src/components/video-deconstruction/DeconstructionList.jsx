import { IconAlertTriangle, IconCircleCheck, IconLoader2, IconVideo } from "@tabler/icons-react";

export function DeconstructionList({ creative }) {
  return <aside className="workflow-rail"><div className="workflow-rail__heading"><IconVideo size={16} /><strong>拆解任务</strong><small>{creative.workflow.deconstructions.length}</small></div><div className="workflow-rail__list">{creative.workflow.deconstructions.map((item) => { const Icon = item.status === "completed" ? IconCircleCheck : item.status === "running" ? IconLoader2 : IconAlertTriangle; return <button className={`rail-item ${creative.selectedDeconstruction?.id === item.id ? "is-active" : ""}`} key={item.id} onClick={() => creative.selectDeconstruction(item.id)} type="button"><Icon className={item.status === "running" ? "spin" : ""} size={16} /><span><strong>{item.title}</strong><small>{item.status === "completed" ? "结果待确认" : item.status === "running" ? "处理中" : "需要恢复"}</small></span></button>; })}</div></aside>;
}
