import { IconChevronDown, IconLoader2, IconX } from "@tabler/icons-react";
import { useState } from "react";

const initialForm = {
  name: "",
  goal: "账号定位内容",
  count: 6,
  template: "账号默认模板",
  source: "当前账号知识库",
  cadence: "完成后确认发布",
};

export function NewBatchDialog({ open, accountName, onClose, onSubmit }) {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  if (!open) return null;

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setError("请输入批次名称");
      return;
    }
    setSubmitting(true);
    const created = await onSubmit({ ...form, name: form.name.trim() });
    setSubmitting(false);
    if (created) setForm(initialForm);
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="batch-dialog" onSubmit={submit}>
        <div className="dialog-header">
          <div><span className="dialog-eyebrow">{accountName}</span><h2>新建生产批次</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose} type="button"><IconX size={18} /></button>
        </div>
        <div className="dialog-body">
          <label className="field field--wide">
            <span>批次名称</span>
            <input
              className={error ? "is-error" : ""}
              value={form.name}
              onChange={(event) => update("name", event.target.value)}
              placeholder="例如：本周工具拆解"
              autoFocus
            />
            {error ? <small className="field-error">{error}</small> : null}
          </label>
          <label className="field"><span>内容目标</span><select value={form.goal} onChange={(event) => update("goal", event.target.value)}><option>账号定位内容</option><option>知识库补充内容</option><option>热点响应内容</option></select></label>
          <label className="field"><span>生成数量</span><input min="1" max="20" type="number" value={form.count} onChange={(event) => update("count", event.target.value)} /></label>
          <label className="field"><span>模板</span><select value={form.template} onChange={(event) => update("template", event.target.value)}><option>账号默认模板</option><option>快速口播</option><option>步骤演示</option></select></label>
          <label className="field"><span>素材来源</span><select value={form.source} onChange={(event) => update("source", event.target.value)}><option>当前账号知识库</option><option>本地工作区</option><option>稍后补充</option></select></label>
          <label className="field field--wide"><span>发布节奏</span><select value={form.cadence} onChange={(event) => update("cadence", event.target.value)}><option>完成后确认发布</option><option>每天一条</option><option>仅生成，不发布</option></select></label>
          <details className="advanced-options"><summary>高级参数 <IconChevronDown size={15} /></summary><p>Provider、知识快照和合成策略由账号配置总线继承。</p></details>
        </div>
        <div className="dialog-actions">
          <button className="ghost-button" onClick={onClose} type="button">取消</button>
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? <IconLoader2 className="spin" size={17} /> : null}
            {submitting ? "创建中" : "创建批次"}
          </button>
        </div>
      </form>
    </div>
  );
}
