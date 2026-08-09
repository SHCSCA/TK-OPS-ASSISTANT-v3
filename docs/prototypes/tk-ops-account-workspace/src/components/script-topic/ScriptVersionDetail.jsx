import { IconCheck, IconClock } from "@tabler/icons-react";

export function ScriptVersionDetail({ creative, script }) {
  return <div className="detail-stack"><div className="detail-summary"><span>当前版本</span><strong>v{script.revision}</strong><small>{script.updated} · {script.status === "adopted" ? "已作为分镜基线" : "尚未采用"}</small></div><section className="detail-section"><h3>版本记录</h3><div className="version-list">{script.versions.map((version) => <div key={version.id}><IconClock size={15} /><span><strong>{version.label} · {version.source}</strong><small>{version.note}</small></span><em>{version.status === "adopted" ? "已采用" : "历史"}</em></div>)}</div></section>{script.status !== "adopted" ? <button className="primary-button" onClick={() => creative.adoptScript(script.id)} type="button"><IconCheck size={16} />采用当前版本</button> : null}</div>;
}
