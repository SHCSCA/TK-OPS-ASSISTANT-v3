import { ResultCheckbox, ResultDataTable } from "./ResultDataTable.jsx";

const columns = [
  { id: "select", label: "选择", className: "result-col-select" },
  { id: "time", label: "时间段", className: "result-col-time" },
  { id: "copy", label: "脚本文案", className: "result-col-copy" },
  { id: "role", label: "段落作用", className: "result-col-role" },
  { id: "confidence", label: "置信度", className: "result-col-confidence" },
];

export function ScriptSegmentsResult({ onToggle, segments, selectedIds }) {
  return <ResultDataTable ariaLabel="视频脚本文案" className="script-result-table" columns={columns}>{segments.map((segment) => { const selected = selectedIds.includes(segment.id); return <tr className={selected ? "is-selected" : ""} key={segment.id}><td><ResultCheckbox checked={selected} label={`选择 ${segment.start} 到 ${segment.end} 的脚本文案`} onChange={() => onToggle(segment.id)} /></td><td><span className="result-time">{segment.start}<i>—</i>{segment.end}</span></td><td><p className="result-copy" title={segment.text}>{segment.text}</p></td><td><span className="result-role">{segment.role}</span></td><td><span className={`confidence-badge confidence-badge--${segment.confidence === "高" ? "high" : segment.confidence === "中" ? "medium" : "low"}`}>{segment.confidence}</span></td></tr>; })}</ResultDataTable>;
}
