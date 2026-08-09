import { useState } from "react";
import { IconDeviceFloppy, IconSparkles } from "@tabler/icons-react";

export function ScriptWorkspace({ creative, onOpenVersion }) {
  const item = creative.selectedContentItem;
  const script = creative.selectedScript;
  const [mode, setMode] = useState("structured");

  if (!item) return <section className="workflow-main empty-workflow"><strong>从一个选题开始</strong><span>手动创建、AI 推荐或从拆解结果建立内容对象。</span><button className="primary-button" onClick={() => creative.openTopicDialog()} type="button">新建选题</button></section>;
  if (!script) return <section className="workflow-main empty-workflow"><strong>选题已就绪</strong><span>{item.topicBrief.angle || "可以直接按账号定位生成第一版脚本。"}</span><button className="primary-button" onClick={() => creative.generateScript()} type="button"><IconSparkles size={16} />AI 生成脚本</button></section>;

  const adopted = script.status === "adopted" && script.adoptedRevision === script.revision;
  return (
    <section className="workflow-main">
      <header className="workspace-card-header">
        <div><span className="section-kicker">脚本工作区</span><h2>{script.title}</h2></div>
        <div className="inline-status"><span className={`status-pill status-pill--${adopted ? "ready" : script.status === "running" ? "ai" : "warning"}`}>{adopted ? "已采用" : script.status === "running" ? "AI 生成中" : "待确认"}</span><button className="text-action" onClick={() => onOpenVersion(script)} type="button">v{script.revision}</button></div>
      </header>
      <div className="segmented-control" role="tablist">
        <button aria-selected={mode === "structured"} className={mode === "structured" ? "is-active" : ""} onClick={() => setMode("structured")} role="tab" type="button">结构预览</button>
        <button aria-selected={mode === "raw"} className={mode === "raw" ? "is-active" : ""} onClick={() => setMode("raw")} role="tab" type="button">正文编辑</button>
      </div>
      {mode === "structured" ? <div className="script-sections">{script.sections.map((section, index) => <article key={section.label}><span>{String(index + 1).padStart(2, "0")}</span><div><small>{section.label}</small><p>{section.value}</p></div></article>)}</div> : <textarea aria-label="脚本正文" className="script-editor" value={creative.scriptDraft.raw} onChange={(event) => creative.setScriptDraftRaw(event.target.value)} />}
      <footer className="workspace-actions">
        <div>{mode === "raw" ? <button className="secondary-button" disabled={!creative.scriptDraftDirty} onClick={creative.saveScriptDraft} type="button"><IconDeviceFloppy size={16} />保存修改</button> : null}<button className="secondary-button ai-secondary" disabled={script.status === "running"} onClick={() => creative.generateScript(script.id)} type="button"><IconSparkles size={16} />AI 优化</button></div>
        <small className="workspace-hint">采用与进入分镜由顶部主动作完成</small>
      </footer>
    </section>
  );
}
