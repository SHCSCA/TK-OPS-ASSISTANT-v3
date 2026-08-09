import { IconCheck, IconLoader2, IconSparkles, IconVideo, IconX } from "@tabler/icons-react";
import { prototypeConfig } from "../../config/prototypeConfig.js";

const sources = [
  { id: "manual", label: "手动创建" },
  { id: "ai", label: "AI 推荐" },
  { id: "deconstruction", label: "视频拆解" },
];

export function TopicCreateDialog({ creative, pillars }) {
  const dialog = creative.topicDialog;
  if (!dialog.open) return null;
  const completedTasks = creative.deconstruction.deconstructions.filter((item) => item.status === "completed");
  const sourceTask = creative.deconstruction.selectedDeconstruction?.status === "completed" ? creative.deconstruction.selectedDeconstruction : completedTasks[0];

  function submitFromDeconstruction() {
    const structure = sourceTask?.result.structureSegments[0];
    const keyword = sourceTask?.result.keywords[0];
    creative.submitTopicDialog({
      angle: structure?.purpose || "复用拆解结构生成新角度",
      audience: "当前账号目标受众",
      pillar: pillars[0] || "工具拆解",
      sourceLabel: `${sourceTask.title} · ${structure?.start || "00:00"}–${structure?.end || "00:36"}`,
      sourceType: "deconstruction",
      tags: sourceTask.result.keywords.slice(0, 3).map((item) => item.label),
      targetDuration: 45,
      title: keyword ? `${keyword.label}的三段式讲解` : `${sourceTask.title} · 新选题`,
    });
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="batch-dialog topic-create-dialog" role="dialog" aria-modal="true" aria-labelledby="topic-create-title">
        <header className="dialog-header">
          <div><span className="dialog-eyebrow">当前账号 · 独立内容对象</span><h2 id="topic-create-title">新建选题</h2></div>
          <button className="icon-button" aria-label="关闭新建选题" onClick={creative.closeTopicDialog} type="button"><IconX size={18} /></button>
        </header>
        <div className="topic-source-tabs" role="tablist">
          {sources.map((source) => <button aria-selected={dialog.source === source.id} className={dialog.source === source.id ? "is-active" : ""} key={source.id} onClick={() => creative.setTopicSource(source.id)} role="tab" type="button">{source.label}</button>)}
        </div>
        <div className="topic-create-dialog__body">
          {dialog.source === "manual" ? <ManualTopicForm creative={creative} pillars={pillars} /> : null}
          {dialog.source === "ai" ? <AITopicSuggestions creative={creative} /> : null}
          {dialog.source === "deconstruction" ? <DeconstructionTopicSource creative={creative} tasks={completedTasks} task={sourceTask} /> : null}
        </div>
        <footer className="dialog-actions">
          <button className="ghost-button" onClick={creative.closeTopicDialog} type="button">取消</button>
          {dialog.source === "ai" && !dialog.suggestions.length ? <button className="primary-button" disabled={dialog.generating} onClick={creative.generateTopicSuggestions} type="button">{dialog.generating ? <IconLoader2 className="spin" size={16} /> : <IconSparkles size={16} />}{dialog.generating ? "生成中" : "生成候选"}</button> : null}
          {dialog.source === "ai" && dialog.suggestions.length ? <button className="primary-button" disabled={dialog.submitting || !dialog.selectedSuggestionIds.length} onClick={() => creative.submitTopicDialog()} type="button">{dialog.submitting ? <IconLoader2 className="spin" size={16} /> : <IconCheck size={16} />}采用所选选题</button> : null}
          {dialog.source === "manual" ? <button className="primary-button" disabled={dialog.submitting} onClick={() => creative.submitTopicDialog()} type="button">{dialog.submitting ? <IconLoader2 className="spin" size={16} /> : <IconCheck size={16} />}创建选题</button> : null}
          {dialog.source === "deconstruction" ? <button className="primary-button" disabled={dialog.submitting || !sourceTask} onClick={submitFromDeconstruction} type="button">{dialog.submitting ? <IconLoader2 className="spin" size={16} /> : <IconVideo size={16} />}从拆解创建</button> : null}
        </footer>
      </section>
    </div>
  );
}

function ManualTopicForm({ creative, pillars }) {
  const form = creative.topicDialog.form;
  return <div className="topic-form-grid">
    <label className="field field--wide"><span>选题标题 *</span><input autoFocus maxLength={80} onChange={(event) => creative.setTopicDialogField("title", event.target.value)} placeholder="例如：一条内容如何进入批量生产" value={form.title} /></label>
    <label className="field"><span>内容支柱 *</span><select onChange={(event) => creative.setTopicDialogField("pillar", event.target.value)} value={form.pillar}><option value="">请选择</option>{pillars.map((pillar) => <option key={pillar}>{pillar}</option>)}</select></label>
    <label className="field"><span>目标时长</span><select onChange={(event) => creative.setTopicDialogField("targetDuration", Number(event.target.value))} value={form.targetDuration}>{prototypeConfig.content.targetDurations.map((seconds) => <option key={seconds} value={seconds}>{seconds} 秒</option>)}</select></label>
    <label className="field"><span>目标受众</span><input onChange={(event) => creative.setTopicDialogField("audience", event.target.value)} placeholder="默认继承账号定位" value={form.audience} /></label>
    <label className="field"><span>来源或参考</span><input onChange={(event) => creative.setTopicDialogField("sourceLabel", event.target.value)} placeholder="可选，仅保存已授权来源摘要" value={form.sourceLabel} /></label>
    <label className="field field--wide"><span>创作角度</span><textarea maxLength={160} onChange={(event) => creative.setTopicDialogField("angle", event.target.value)} placeholder="一句话说明这条内容从哪个角度切入" value={form.angle} /></label>
  </div>;
}

function AITopicSuggestions({ creative }) {
  const dialog = creative.topicDialog;
  if (!dialog.suggestions.length) return <div className="topic-source-empty"><IconSparkles size={24} /><strong>按账号定位生成候选</strong><span>只读取当前账号定位和演示知识快照，不会混用其他账号内容。</span></div>;
  return <div className="topic-suggestion-list">{dialog.suggestions.map((item) => <button className={dialog.selectedSuggestionIds.includes(item.id) ? "is-selected" : ""} key={item.id} onClick={() => creative.toggleTopicSuggestion(item.id)} type="button"><span className="topic-suggestion-check">{dialog.selectedSuggestionIds.includes(item.id) ? <IconCheck size={14} /> : null}</span><span><strong>{item.title}</strong><small>{item.pillar} · {item.angle}</small><em>{item.sourceLabel}</em></span></button>)}</div>;
}

function DeconstructionTopicSource({ creative, task, tasks }) {
  if (!task) return <div className="topic-source-empty"><IconVideo size={24} /><strong>暂无可用拆解结果</strong><span>先完成一个视频拆解任务，再从证据创建选题。</span></div>;
  return <div className="deconstruction-topic-source"><label className="field"><span>拆解任务</span><select onChange={(event) => creative.deconstruction.selectDeconstruction(event.target.value)} value={task.id}>{tasks.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><div className="source-evidence-summary"><span><small>结构</small><strong>{task.result.structureSegments.map((item) => item.label).join(" / ")}</strong></span><span><small>关键词</small><strong>{task.result.keywords.slice(0, 3).map((item) => item.label).join("、")}</strong></span><span><small>来源证据</small><strong>{task.source}</strong></span></div></div>;
}
