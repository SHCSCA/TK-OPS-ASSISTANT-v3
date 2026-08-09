import { IconCircle, IconTargetArrow } from "@tabler/icons-react";

export function TopicBriefRail({ creative }) {
  const items = creative.contentItems;
  return (
    <aside className="workflow-rail">
      <div className="workflow-rail__heading"><IconTargetArrow size={16} /><strong>选题</strong><small>{items.length}</small></div>
      <div className="workflow-rail__list">
        {items.map((item) => {
          const active = creative.selectedContentItem?.id === item.id;
          return (
            <button className={`rail-item ${active ? "is-active" : ""}`} key={item.id} onClick={() => creative.selectContentItem(item.id)} type="button">
              <IconCircle size={14} />
              <span><strong>{item.title}</strong><small>{item.topicBrief.pillar} · {creative.contentStageLabels[item.stage]}</small></span>
            </button>
          );
        })}
        {!items.length ? <div className="rail-empty">当前账号还没有选题</div> : null}
      </div>
      <button className="rail-create" onClick={() => creative.openTopicDialog()} type="button">+ 新建选题</button>
    </aside>
  );
}
