import { IconX } from "@tabler/icons-react";

export function ModelCapabilityDetail({ model, provider, onClose }) {
  if (!model) return null;
  return <aside aria-label="模型能力详情" className="detail-panel model-detail"><div className="detail-panel__header"><div><span>{provider?.name || "未绑定 Provider"}</span><h2>{model.displayName}</h2></div><button aria-label="关闭模型详情" className="icon-button" onClick={onClose} type="button"><IconX size={18} /></button></div><div className="detail-panel__body"><section className="detail-section"><h3>能力边界</h3><CapabilityCompare label="模型声明" values={model.declaredAbilities} /><CapabilityCompare label="当前适配器可用" values={model.adapterAbilities} /></section><section className="detail-section"><h3>输入与参数</h3><dl className="compact-definition"><div><dt>输入</dt><dd>{model.adapterInputModalities.join("、")}</dd></div><div><dt>限制</dt><dd>{model.contextLimit}</dd></div><div><dt>发现来源</dt><dd>{model.sourceLabel}</dd></div><div><dt>参数 Schema</dt><dd>{Object.keys(model.parameterSchema).length ? Object.keys(model.parameterSchema).join("、") : "尚未验证"}</dd></div></dl></section>{model.contractIssues.length ? <section className="detail-section detail-section--warning"><h3>契约差异</h3>{model.contractIssues.map((issue) => <p key={issue}>{issue}</p>)}</section> : null}</div></aside>;
}

function CapabilityCompare({ label, values }) {
  return <div className="capability-compare"><strong>{label}</strong><span>{values.map((value) => <i key={value}>{value}</i>)}</span></div>;
}
