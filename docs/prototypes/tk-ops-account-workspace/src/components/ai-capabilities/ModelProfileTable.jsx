import { IconChevronRight, IconCircleCheck, IconCircleX } from "@tabler/icons-react";

export function ModelProfileTable({ models, providers, onOpen, onToggle }) {
  return <div className="ai-data-table" role="table" aria-label="模型配置"><div className="ai-data-table__head" role="row"><span>模型</span><span>Provider</span><span>适配器能力</span><span>契约</span><span>启用</span><span /></div>{models.map((model) => {
    const provider = providers.find((item) => item.id === model.providerProfileId);
    return <div className="ai-data-table__row" key={model.id} role="row"><span><strong>{model.displayName}</strong><small>{model.modelId}</small></span><span>{provider?.name || "未绑定"}</span><span className="ability-line">{model.adapterAbilities.slice(0, 3).map((ability) => <i key={ability}>{ability}</i>)}</span><span className={model.contractVerified ? "contract-state is-ready" : "contract-state is-warning"}>{model.contractVerified ? <IconCircleCheck size={15} /> : <IconCircleX size={15} />}{model.contractVerified ? "已验证" : "待验证"}</span><span><button aria-label={`${model.enabled ? "停用" : "启用"}${model.displayName}`} aria-pressed={model.enabled} className={model.enabled ? "mini-switch is-on" : "mini-switch"} onClick={() => onToggle(model.id)} type="button"><i /></button></span><span><button aria-label={`查看${model.displayName}详情`} className="icon-button" onClick={() => onOpen(model.id)} type="button"><IconChevronRight size={17} /></button></span></div>;
  })}</div>;
}
