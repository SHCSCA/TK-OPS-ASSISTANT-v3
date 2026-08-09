import { IconAlertTriangle, IconCheck, IconCircle, IconLoader2 } from "@tabler/icons-react";

const statusIcons = {
  active: IconLoader2,
  blocked: IconAlertTriangle,
  completed: IconCheck,
  confirmed: IconCheck,
  not_started: IconCircle,
  review: IconCircle,
};

export function CreativeChainHeader({ action, contentItem, onOpenTopic, secondaryAction, stages }) {
  return (
    <section className="creative-chain-header">
      <div className="creative-chain-header__title">
        <div>
          <span className="section-kicker">当前创作对象</span>
          <h2>{contentItem?.title || "尚未建立内容"}</h2>
        </div>
        <div className="creative-chain-header__actions">
          {secondaryAction}
          {contentItem && onOpenTopic ? <button className="ghost-button" onClick={onOpenTopic} type="button">新建选题</button> : null}
          {action}
        </div>
      </div>
      <ol className="creative-stage-rail" aria-label="创作阶段">
        {stages.map((stage) => {
          const StatusIcon = statusIcons[stage.status] || IconCircle;
          return (
            <li className={`creative-stage creative-stage--${stage.status}`} key={stage.id}>
              <span><StatusIcon className={stage.status === "active" ? "spin" : ""} size={14} /></span>
              <small>{stage.label}</small>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
