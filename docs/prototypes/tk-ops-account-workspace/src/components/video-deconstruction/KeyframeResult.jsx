import { IconPhotoOff, IconRefresh } from "@tabler/icons-react";
import { ResultCheckbox, ResultDataTable } from "./ResultDataTable.jsx";

const columns = [
  { id: "select", label: "选择", className: "result-col-select" },
  { id: "preview", label: "预览", className: "result-col-preview" },
  { id: "time", label: "时间点", className: "result-col-frame-time" },
  { id: "role", label: "镜头作用", className: "result-col-frame-role" },
  { id: "summary", label: "画面摘要", className: "result-col-frame-summary" },
  { id: "reuse", label: "可复用方向", className: "result-col-reuse" },
];

export function KeyframeResult({ frames, onRetry, onToggle, selectedIds }) {
  const realFrames = frames.filter((frame) => frame.imageRef);
  if (!realFrames.length) return <div className="keyframe-empty"><IconPhotoOff size={24} /><strong>尚未提取到真实关键帧</strong><span>当前结果不能作为分镜或图片资产使用，脚本与结构证据仍已保留。</span><button className="secondary-button" onClick={onRetry} type="button"><IconRefresh size={15} />重新提取</button></div>;
  return <ResultDataTable ariaLabel="视频关键帧" className="keyframe-result-table" columns={columns}>{realFrames.map((frame) => { const selected = selectedIds.includes(frame.id); return <tr className={selected ? "is-selected" : ""} key={frame.id}><td><ResultCheckbox checked={selected} label={`选择 ${frame.time} 的关键帧`} onChange={() => onToggle(frame.id)} /></td><td><img alt={`${frame.time} ${frame.label}`} className="keyframe-thumbnail" src={frame.imageRef} /></td><td><span className="frame-time">{frame.time}</span></td><td><span className="result-role">{frame.label}</span></td><td><p className="result-copy">{frame.note}</p></td><td><span className="reuse-label">{frame.reuse}</span></td></tr>; })}</ResultDataTable>;
}
