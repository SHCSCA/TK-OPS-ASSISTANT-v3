import { IconCheck, IconLoader2, IconX } from "@tabler/icons-react";

export function DeconstructionStages({ stages }) {
  return <div className="deconstruction-stages">{stages.map((stage, index) => <div className={`deconstruction-stage deconstruction-stage--${stage.status}`} key={stage.id}><span>{stage.status === "completed" ? <IconCheck size={14} /> : stage.status === "failed" ? <IconX size={14} /> : stage.status === "active" ? <IconLoader2 className="spin" size={14} /> : index + 1}</span><small>{stage.label}</small></div>)}</div>;
}
