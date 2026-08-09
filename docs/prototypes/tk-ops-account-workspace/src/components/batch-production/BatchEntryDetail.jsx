import { IconAlertTriangle, IconFileText, IconMovie, IconRefresh } from "@tabler/icons-react";
import { getEntryReadiness } from "../../data/productionBatches.js";

export function BatchEntryDetail({ creative, entry, navigate }) {
  const item = creative.contentItems.find((candidate) => candidate.id === entry.contentItemId);
  const script = creative.workflow.scripts.find((candidate) => candidate.contentItemId === entry.contentItemId);
  const board = creative.workflow.storyboards.find((candidate) => candidate.contentItemId === entry.contentItemId);
  const readiness = getEntryReadiness(entry, item, script, board);
  return <div className="detail-stack">
    {entry.blocker ? <div className="detail-alert detail-alert--danger"><IconAlertTriangle size={17} /><strong>{entry.blocker}</strong><p>只阻断当前内容条目，不影响批次中的其他内容。</p></div> : null}
    <section className="detail-section"><h3>不可变创作引用</h3><dl className="compact-dl"><div><dt>内容对象</dt><dd>{entry.contentItemReference.contentItemId}</dd></div><div><dt>脚本</dt><dd>{entry.contentItemReference.scriptVersionId || "尚未采用"}</dd></div><div><dt>分镜</dt><dd>{entry.contentItemReference.storyboardVersionId || "尚未确认"}</dd></div></dl></section>
    <section className="detail-section"><h3>阶段准备度</h3><dl className="compact-dl">{Object.entries(readiness).map(([key, value]) => <div key={key}><dt>{stageLabels[key]}</dt><dd>{value}</dd></div>)}</dl></section>
    <section className="detail-section"><h3>返回创作对象</h3><button className="detail-action" onClick={() => { creative.selectContentItem(entry.contentItemId); navigate("scripts"); }} type="button"><IconFileText size={17} />打开脚本与选题</button><button className="detail-action" onClick={() => { creative.selectContentItem(entry.contentItemId); navigate("storyboard"); }} type="button"><IconMovie size={17} />打开分镜规划</button>{entry.status === "failed" || entry.blocker ? <button className="detail-action" onClick={() => creative.production.retryEntry(entry.id)} type="button"><IconRefresh size={17} />重试当前条目</button> : null}</section>
  </div>;
}

const stageLabels = { output: "输出", production: "生产", script: "脚本", storyboard: "分镜", topic: "选题" };
