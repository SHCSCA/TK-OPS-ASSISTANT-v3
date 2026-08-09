import { IconAlertTriangle, IconBan, IconCheck, IconClock, IconLoader2, IconPlayerPause, IconRefresh } from "@tabler/icons-react";

const statusMeta = {
  cancelling: { label: "正在取消", Icon: IconPlayerPause },
  completed: { label: "完成", Icon: IconCheck },
  failed: { label: "失败", Icon: IconAlertTriangle },
  queued: { label: "排队中", Icon: IconClock },
  running: { label: "运行中", Icon: IconLoader2 },
  skipped: { label: "已跳过", Icon: IconBan },
};

export function GenerationPipeline({ run, onOpenStep, onRetry }) {
  if (!run) return <div className="pipeline-empty">此演示批次尚未创建 AI 节点记录</div>;
  return <div className="generation-pipeline">{run.steps.map((step) => {
    const meta = statusMeta[step.status];
    const Icon = meta.Icon;
    return <article className={`generation-node generation-node--${step.status}`} key={step.id}><button className="generation-node__main" onClick={() => onOpenStep(step)} type="button"><span className="generation-node__icon"><Icon className={step.status === "running" ? "spin" : ""} size={17} /></span><span className="generation-node__copy"><strong>{step.name}</strong><small>{step.skipReason || step.action || step.model}</small></span><span className="generation-node__progress"><i><b style={{ width: `${step.progress}%` }} /></i><small>{step.itemTotal ? `${step.itemCurrent} / ${step.itemTotal} · ` : ""}{meta.label}</small></span><span className="generation-node__time">{step.duration}</span></button>{step.status === "failed" ? <button className="text-action" onClick={() => onRetry(run.batchId, step.id)} type="button"><IconRefresh size={15} />局部重试</button> : <button className="text-action" onClick={() => onOpenStep(step)} type="button">详情</button>}</article>;
  })}</div>;
}
