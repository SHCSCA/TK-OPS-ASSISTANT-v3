import { IconBookUpload, IconHistory, IconRefresh, IconShieldCheck } from "@tabler/icons-react";
import { PageSection } from "../components/PageSection.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

const statusLabels = { error: "索引失败", ready: "已就绪", stale: "需要更新" };

export function StrategyKnowledge({ state }) {
  const { strategy, knowledge } = state.workspace;
  const emptyState = resolvePageEmptyState("knowledge", state.dataScenario, knowledge.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={(action) => state.notify(action === "edit-positioning" ? "定位编辑已打开" : "来源导入器已打开", "info")} /></div>;
  return (
    <div className="page-stack page-enter">
      <PageSection
        title="账号定位"
        meta={strategy.version}
        action={<button className="secondary-button" onClick={() => state.notify("定位编辑已打开", "info")} type="button">编辑定位</button>}
      >
        <div className="strategy-summary">
          <div><p>{strategy.summary}</p><div className="tag-row">{strategy.pillars.map((item) => <span key={item}>{item}</span>)}</div></div>
          <div className="strategy-rules"><span><IconShieldCheck size={17} />生成规则</span>{strategy.rules.map((rule) => <small key={rule}>{rule}</small>)}</div>
        </div>
      </PageSection>
      <PageSection
        title="知识来源"
        meta="生成只读取当前账号已启用的来源"
        action={<button className="primary-button" onClick={() => state.notify("来源导入器已打开", "info")} type="button"><IconBookUpload size={17} />导入资料</button>}
      >
        <div className="source-list">
          {knowledge.map((source) => (
            <article className="source-row" key={source.id}>
              <span className="source-type">{source.type}</span>
              <span className="source-name"><strong>{source.name}</strong><small>更新于 {source.updated}</small></span>
              <span className={`status-pill status-pill--${source.status === "ready" ? "ready" : source.status === "error" ? "danger" : "warning"}`}>{statusLabels[source.status]}</span>
              <button className="text-action" onClick={() => state.updateKnowledge(source.id)} type="button"><IconRefresh size={15} />{source.status === "ready" ? "刷新" : "重新索引"}</button>
            </article>
          ))}
        </div>
      </PageSection>
      <button className="history-link" onClick={() => state.notify("已打开定位版本记录", "info")} type="button"><IconHistory size={16} />查看定位与知识快照</button>
    </div>
  );
}
