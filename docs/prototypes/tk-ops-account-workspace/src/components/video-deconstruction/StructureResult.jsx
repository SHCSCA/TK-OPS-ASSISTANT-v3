import { ResultCheckbox, ResultDataTable } from "./ResultDataTable.jsx";

const columns = [
  { id: "select", label: "选择", className: "result-col-select" },
  { id: "segment", label: "结构段", className: "result-col-structure" },
  { id: "time", label: "时间", className: "result-col-structure-time" },
  { id: "ratio", label: "时长占比", className: "result-col-structure-ratio" },
  { id: "purpose", label: "作用", className: "result-col-purpose" },
  { id: "copy", label: "对应文案", className: "result-col-structure-copy" },
  { id: "evidence", label: "证据关键词", className: "result-col-structure-evidence" },
];

export function StructureResult({ onToggle, segments, selectedIds, summary }) {
  return <div className="structure-result"><section className="structure-summary" aria-label="视频特点总结"><div><span className="section-kicker">视频特点</span><p>{summary?.description || "尚未形成视频特点总结。"}</p></div><dl><div><dt>主要类型</dt><dd>{summary?.narrativeType || "待分析"}</dd></div><div><dt>总时长</dt><dd>{summary?.duration || "--"}</dd></div><div><dt>结构</dt><dd>{segments.length} 段</dd></div></dl>{summary?.tags?.length ? <div className="feature-tags">{summary.tags.slice(0, 5).map((tag) => <span key={tag}>{tag}</span>)}</div> : <span className="feature-tags-empty">尚未形成特点标签</span>}</section><div className="structure-ratio" aria-label="内容结构比例">{segments.map((segment) => <button aria-pressed={selectedIds.includes(segment.id)} className={selectedIds.includes(segment.id) ? "is-selected" : ""} key={segment.id} onClick={() => onToggle(segment.id)} style={{ flexBasis: `${segment.percent}%` }} title={segment.purpose} type="button"><strong>{segment.label}</strong><small>{segment.percent}%</small></button>)}</div><ResultDataTable ariaLabel="视频内容结构" className="structure-result-table" columns={columns}>{segments.map((segment) => { const selected = selectedIds.includes(segment.id); return <tr className={selected ? "is-selected" : ""} key={segment.id}><td><ResultCheckbox checked={selected} label={`选择结构段 ${segment.label}`} onChange={() => onToggle(segment.id)} /></td><td><strong className="structure-name">{segment.label}</strong></td><td><span className="result-time">{segment.start}<i>—</i>{segment.end}</span></td><td><span className="weight-value">{segment.percent}%<i aria-hidden="true"><b style={{ width: `${segment.percent}%` }} /></i></span></td><td><p className="result-purpose">{segment.purpose}</p></td><td><p className="result-copy">{segment.copy || segment.purpose}</p></td><td><span className="evidence-keywords">{(segment.evidenceKeywords || []).slice(0, 3).map((value) => <i key={value}>{value}</i>)}</span></td></tr>; })}</ResultDataTable></div>;
}
