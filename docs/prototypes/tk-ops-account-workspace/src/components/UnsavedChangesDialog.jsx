import { IconDeviceFloppy, IconTrash, IconX } from "@tabler/icons-react";

export function UnsavedChangesDialog({ accountName, onCancel, onDiscard, onSave, open }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation">
      <section aria-labelledby="unsaved-title" aria-modal="true" className="batch-dialog unsaved-dialog" role="dialog">
        <header className="dialog-header">
          <div><span className="dialog-eyebrow">未保存修改</span><h2 id="unsaved-title">切换账号前处理脚本</h2></div>
          <button aria-label="取消切换账号" className="icon-button" onClick={onCancel} type="button"><IconX size={18} /></button>
        </header>
        <div className="unsaved-dialog__body"><p>当前脚本正文已修改。切换到“{accountName}”前，请保存或放弃本次修改。</p><small>选择取消会留在当前账号，草稿保持不变。</small></div>
        <footer className="dialog-actions">
          <button className="ghost-button" onClick={onCancel} type="button">取消</button>
          <button className="secondary-button" onClick={onDiscard} type="button"><IconTrash size={16} />放弃并切换</button>
          <button className="primary-button" onClick={onSave} type="button"><IconDeviceFloppy size={16} />保存并切换</button>
        </footer>
      </section>
    </div>
  );
}
