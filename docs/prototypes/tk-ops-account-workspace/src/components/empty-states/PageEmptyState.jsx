import { IconArrowRight, IconFolderPlus } from "@tabler/icons-react";

export function PageEmptyState({ definition, onAction }) {
  if (!definition) return null;
  return <section className="page-empty-state"><span><IconFolderPlus size={20} /></span><small>{definition.eyebrow}</small><h2>{definition.title}</h2><p>{definition.description}</p><div><button className="primary-button" onClick={() => onAction(definition.actionId)} type="button">{definition.actionLabel}<IconArrowRight size={16} /></button>{definition.secondaryActionId ? <button className="secondary-button" onClick={() => onAction(definition.secondaryActionId)} type="button">{definition.secondaryLabel}</button> : null}</div></section>;
}
