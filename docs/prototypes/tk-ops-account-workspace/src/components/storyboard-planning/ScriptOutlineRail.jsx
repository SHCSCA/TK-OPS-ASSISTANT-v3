import { IconFileText, IconRefreshAlert } from "@tabler/icons-react";
import { hasStoryboardRevisionMismatch } from "../../data/creativeWorkflow.js";

export function ScriptOutlineRail({ script, storyboard }) {
  const mismatch = hasStoryboardRevisionMismatch(script, storyboard);
  return <aside className="workflow-rail"><div className="workflow-rail__heading"><IconFileText size={16} /><strong>脚本大纲</strong><small>v{script?.revision || "-"}</small></div>{mismatch ? <div className="sync-warning"><IconRefreshAlert size={16} /><span><strong>脚本已更新</strong><small>当前分镜基于 v{storyboard.sourceScriptRevision}</small></span></div> : null}<div className="outline-list">{script?.sections.map((section, index) => <div key={section.label}><span>{index + 1}</span><p><strong>{section.label}</strong><small>{section.value}</small></p></div>)}</div></aside>;
}
