import { IconPlus } from "@tabler/icons-react";

export function PromptProfileTable({ onCreate, onSelect, prompts, selectedPromptId }) {
  return <aside className="prompt-list"><header><div><strong>Prompt Profiles</strong><small>{prompts.length} 个版本入口</small></div><button aria-label="新建 Prompt" className="icon-button" onClick={onCreate} type="button"><IconPlus size={17} /></button></header><div>{prompts.map((prompt) => <button className={prompt.id === selectedPromptId ? "is-active" : ""} key={prompt.id} onClick={() => onSelect(prompt.id)} type="button"><span><strong>{prompt.name}</strong><small>{prompt.capabilityId}</small></span><i>v{prompt.version}</i></button>)}</div></aside>;
}
