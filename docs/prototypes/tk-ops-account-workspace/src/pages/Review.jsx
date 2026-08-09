import { IconArrowBackUp, IconBulb, IconFileAnalytics } from "@tabler/icons-react";
import { PageSection } from "../components/PageSection.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function Review({ state }) {
  const emptyState = resolvePageEmptyState("review", state.dataScenario, state.workspace.review.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.navigate("publishing")} /></div>;
  return (
    <div className="page-stack page-enter">
      <div className="review-note"><IconFileAnalytics size={19} /><span><strong>复盘只使用已连接的内容结果</strong><small>下面包含演示建议，用于验证回流交互。</small></span></div>
      <PageSection title="可执行建议" meta="每条建议必须由你确认后回流">
        <div className="review-list">
          {state.workspace.review.map((item) => (
            <article className="review-row" key={item.id}>
              <span className="review-row__icon"><IconBulb size={19} /></span>
              <span><strong>{item.title}</strong><small>{item.evidence}</small></span>
              <span className="status-pill status-pill--brand">回流到 {item.target}</span>
              <button className="secondary-button" onClick={() => state.notify(`建议已加入${item.target}`, "success")} type="button"><IconArrowBackUp size={16} />确认回流</button>
            </article>
          ))}
        </div>
      </PageSection>
    </div>
  );
}
