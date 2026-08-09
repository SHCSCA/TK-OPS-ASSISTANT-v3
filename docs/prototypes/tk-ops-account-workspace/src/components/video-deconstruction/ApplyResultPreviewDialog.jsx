import { IconCheck, IconLoader2, IconX } from "@tabler/icons-react";

const actions = [
  { id: "topic", label: "创建新选题", note: "建立新的内容对象" },
  { id: "script", label: "创建脚本新版本", note: "不覆盖现有脚本" },
  { id: "storyboard", label: "创建分镜新版本", note: "使用结构段生成镜头" },
  { id: "knowledge", label: "写入账号知识库", note: "仅当前账号可用" },
  { id: "asset", label: "保存拆解文档", note: "归档到内容库" },
];

export function ApplyResultPreviewDialog({ creative }) {
  const dialog = creative.deconstruction.applyDialog;
  const item = creative.deconstruction.selectedDeconstruction;
  if (!dialog.open || !item) return null;
  const targetRequired = ["script", "storyboard"].includes(dialog.action);
  return <div className="modal-backdrop" role="presentation"><section className="batch-dialog apply-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="apply-preview-title">
    <header className="dialog-header"><div><span className="dialog-eyebrow">默认新建对象或版本</span><h2 id="apply-preview-title">应用拆解结果</h2></div><button className="icon-button" aria-label="关闭应用结果" onClick={creative.deconstruction.closeApplyDialog} type="button"><IconX size={18} /></button></header>
    <div className="apply-preview-body"><div className="apply-action-list">{actions.map((action) => <button className={dialog.action === action.id ? "is-active" : ""} key={action.id} onClick={() => creative.deconstruction.setApplyField("action", action.id)} type="button"><span><strong>{action.label}</strong><small>{action.note}</small></span>{dialog.action === action.id ? <IconCheck size={15} /> : null}</button>)}</div><div className="apply-impact-preview"><span className="section-kicker">影响预览</span><h3>{impactTitle(dialog.action)}</h3><dl><div><dt>来源</dt><dd>{item.title}</dd></div><div><dt>脚本片段</dt><dd>{dialog.scriptSegmentIds.length} 段</dd></div><div><dt>关键词</dt><dd>{dialog.keywordIds.length} 个</dd></div><div><dt>关键帧</dt><dd>{dialog.keyframeIds.length} 个真实帧</dd></div><div><dt>结构</dt><dd>{dialog.structureIds.length} 段</dd></div><div><dt>覆盖现有内容</dt><dd>不会</dd></div></dl>{targetRequired ? <label className="field"><span>目标内容对象</span><select onChange={(event) => creative.deconstruction.setApplyField("targetContentItemId", event.target.value)} value={dialog.targetContentItemId}><option value="">请选择</option>{creative.contentItems.map((contentItem) => <option key={contentItem.id} value={contentItem.id}>{contentItem.title}</option>)}</select></label> : null}</div></div>
    <footer className="dialog-actions"><button className="ghost-button" onClick={creative.deconstruction.closeApplyDialog} type="button">取消</button><button className="primary-button" disabled={dialog.submitting || (targetRequired && !dialog.targetContentItemId)} onClick={creative.deconstruction.submitApply} type="button">{dialog.submitting ? <IconLoader2 className="spin" size={16} /> : <IconCheck size={16} />}{dialog.submitting ? "应用中" : "确认应用"}</button></footer>
  </section></div>;
}

function impactTitle(action) {
  if (action === "topic") return "将创建 1 个新选题";
  if (action === "script") return "将创建脚本新版本";
  if (action === "storyboard") return "将创建分镜新版本";
  if (action === "asset") return "将创建 1 个文档资产";
  return "将写入当前账号知识库";
}
