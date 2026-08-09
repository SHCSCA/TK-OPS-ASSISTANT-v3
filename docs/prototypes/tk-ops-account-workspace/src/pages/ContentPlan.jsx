import { IconCalendarPlus, IconCheck, IconSquare } from "@tabler/icons-react";
import { PageSection } from "../components/PageSection.jsx";

export function ContentPlan({ state }) {
  const selectedCount = state.workspace.topics.filter((topic) => topic.selected).length;
  return (
    <div className="page-stack page-enter">
      <PageSection title="内容支柱" meta="来自当前账号定位版本">
        <div className="pillar-row">{state.workspace.strategy.pillars.map((pillar, index) => <article key={pillar}><span>{String(index + 1).padStart(2, "0")}</span><strong>{pillar}</strong></article>)}</div>
      </PageSection>
      <PageSection
        title="本周选题"
        meta={`${selectedCount} 项已选择`}
        action={<button className="primary-button" disabled={!selectedCount} onClick={() => state.setBatchDialogOpen(true)} type="button"><IconCalendarPlus size={17} />从所选内容建批</button>}
      >
        <div className="topic-list">
          {state.workspace.topics.map((topic) => (
            <button className={`topic-row ${topic.selected ? "is-selected" : ""}`} key={topic.id} onClick={() => state.toggleTopic(topic.id)} type="button">
              <span className="topic-check">{topic.selected ? <IconCheck size={16} /> : <IconSquare size={16} />}</span>
              <span><strong>{topic.title}</strong><small>{topic.pillar}</small></span>
            </button>
          ))}
        </div>
      </PageSection>
      <PageSection title="发布节奏" meta="演示排期，不代表真实平台任务">
        <div className="cadence-strip"><span>周一<small>选题确认</small></span><span>周三<small>批量生成</small></span><span>周五<small>确认发布</small></span><span>周日<small>复盘回流</small></span></div>
      </PageSection>
    </div>
  );
}
