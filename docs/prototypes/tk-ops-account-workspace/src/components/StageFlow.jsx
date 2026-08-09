import {
  IconBulb,
  IconFileText,
  IconLayersLinked,
  IconMovie,
  IconSparkles,
  IconUpload,
} from "@tabler/icons-react";
import { prototypeConfig } from "../config/prototypeConfig.js";

const icons = [IconBulb, IconFileText, IconLayersLinked, IconSparkles, IconMovie, IconUpload];

export function StageFlow({ activeStage, batches, onSelect }) {
  const reachedStages = new Set(batches.map((batch) => batch.stage));
  return (
    <section className="section-block stage-section">
      <div className="section-heading">
        <h2>生产流程</h2>
        <span>点击阶段筛选批次</span>
      </div>
      <div className="stage-flow">
        {prototypeConfig.stageOrder.map((stage, index) => {
          const Icon = icons[index];
          const selected = activeStage === stage;
          const active = reachedStages.has(stage) || selected;
          return (
            <button
              className={`stage-node ${active ? "is-reached" : ""} ${selected ? "is-selected" : ""}`}
              key={stage}
              onClick={() => onSelect(selected ? null : stage)}
              type="button"
            >
              <span className="stage-node__icon"><Icon size={17} stroke={1.8} /></span>
              <span>{stage}</span>
              {index < prototypeConfig.stageOrder.length - 1 ? <i className="stage-node__line" /> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
