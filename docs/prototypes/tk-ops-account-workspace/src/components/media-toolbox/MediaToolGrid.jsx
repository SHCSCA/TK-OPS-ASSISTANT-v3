import { mediaTools } from "../../data/mediaTools.js";

export function MediaToolGrid({ onOpen }) {
  return <div className="media-tool-grid">{mediaTools.map(({ id, name, description, icon: Icon }) => <button key={id} onClick={() => onOpen(id)} type="button"><span><Icon size={19} /></span><div><strong>{name}</strong><small>{description}</small></div></button>)}</div>;
}
