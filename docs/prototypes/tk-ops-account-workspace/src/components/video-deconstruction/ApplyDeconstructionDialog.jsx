import { useState } from "react";
import { IconBook, IconFileText, IconHierarchy3, IconX } from "@tabler/icons-react";

const targets = [
  { id: "script", label: "脚本与选题", description: "创建一版可编辑脚本参考", icon: IconFileText },
  { id: "storyboard", label: "分镜规划", description: "导入镜头结构与节奏", icon: IconHierarchy3 },
  { id: "knowledge", label: "账号知识库", description: "保存为当前账号参考", icon: IconBook },
];

export function ApplyDeconstructionDialog({ item, onApply, onClose, open }) {
  const [target, setTarget] = useState("script");
  if (!open) return null;
  return <div className="modal-backdrop"><section className="batch-dialog apply-dialog" role="dialog" aria-modal="true"><header className="dialog-header"><div><span className="dialog-eyebrow">确认回流</span><h2>{item.title}</h2></div><button className="icon-button" aria-label="关闭" onClick={onClose} type="button"><IconX size={18} /></button></header><div className="apply-targets">{targets.map(({ id, label, description, icon: Icon }) => <button className={target === id ? "is-active" : ""} key={id} onClick={() => setTarget(id)} type="button"><Icon size={19} /><span><strong>{label}</strong><small>{description}</small></span></button>)}</div><p className="dialog-safe-note">只写入当前账号工作区；不会覆盖已有内容。</p><footer className="dialog-actions"><button className="secondary-button" onClick={onClose} type="button">取消</button><button className="primary-button" onClick={() => { onApply(item.id, target); onClose(); }} type="button">确认应用</button></footer></section></div>;
}
