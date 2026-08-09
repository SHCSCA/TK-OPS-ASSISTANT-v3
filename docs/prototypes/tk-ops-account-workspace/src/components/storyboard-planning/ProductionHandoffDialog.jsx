import { IconCheck, IconLayersLinked, IconLoader2, IconMovie, IconPlus, IconX } from "@tabler/icons-react";

const modes = [
  { id: "single", icon: IconMovie, label: "生成单条视频", note: "创建仅含当前内容的单项批次" },
  { id: "existing", icon: IconLayersLinked, label: "加入现有批次", note: "与其他已确认内容一起执行" },
  { id: "new", icon: IconPlus, label: "创建新批次", note: "新建批次并加入当前内容" },
];

export function ProductionHandoffDialog({ creative }) {
  const dialog = creative.production.handoff;
  const item = creative.selectedContentItem;
  const script = creative.selectedScript;
  const board = creative.selectedStoryboard;
  if (!dialog.open || !item) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="batch-dialog production-handoff" role="dialog" aria-modal="true" aria-labelledby="production-handoff-title">
        <header className="dialog-header"><div><span className="dialog-eyebrow">已确认创作版本</span><h2 id="production-handoff-title">进入生产</h2></div><button className="icon-button" aria-label="关闭生产交接" onClick={creative.production.closeHandoff} type="button"><IconX size={18} /></button></header>
        <div className="handoff-version-summary">
          <strong>{item.title}</strong>
          <span>脚本 v{script?.revision} · 分镜 v{board?.revision}</span>
          <small>{item.topicBrief.targetDuration} 秒 · {item.topicBrief.pillar}</small>
        </div>
        <div className="handoff-modes" role="radiogroup" aria-label="生产方式">
          {modes.map(({ id, icon: Icon, label, note }) => <button aria-checked={dialog.mode === id} className={dialog.mode === id ? "is-active" : ""} key={id} onClick={() => creative.production.setHandoffField("mode", id)} role="radio" type="button"><Icon size={18} /><span><strong>{label}</strong><small>{note}</small></span>{dialog.mode === id ? <IconCheck size={16} /> : null}</button>)}
        </div>
        {dialog.mode === "existing" ? <label className="field handoff-field"><span>目标批次</span><select onChange={(event) => creative.production.setHandoffField("batchId", event.target.value)} value={dialog.batchId}><option value="">请选择</option>{creative.production.appendableBatches.map((batch) => <option key={batch.id} value={batch.id}>{batch.name} · {batch.stage}</option>)}</select></label> : null}
        {dialog.mode === "new" ? <label className="field handoff-field"><span>批次名称</span><input autoFocus onChange={(event) => creative.production.setHandoffField("name", event.target.value)} placeholder={`${item.title} · 生产批次`} value={dialog.name} /></label> : null}
        <footer className="dialog-actions"><button className="ghost-button" onClick={creative.production.closeHandoff} type="button">取消</button><button className="primary-button" disabled={dialog.submitting} onClick={creative.production.submitHandoff} type="button">{dialog.submitting ? <IconLoader2 className="spin" size={16} /> : <IconCheck size={16} />}{dialog.submitting ? "正在交接" : "确认进入生产"}</button></footer>
      </section>
    </div>
  );
}
