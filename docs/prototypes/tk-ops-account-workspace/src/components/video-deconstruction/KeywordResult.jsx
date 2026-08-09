import { ResultCheckbox, ResultDataTable } from "./ResultDataTable.jsx";

const columns = [
  { id: "select", label: "选择", className: "result-col-select" },
  { id: "keyword", label: "关键词", className: "result-col-keyword" },
  { id: "category", label: "分类", className: "result-col-category" },
  { id: "weight", label: "权重", className: "result-col-weight" },
  { id: "hits", label: "命中", className: "result-col-hits" },
  { id: "evidence", label: "证据", className: "result-col-evidence" },
];

export function KeywordResult({ keywords, onEvidence, onToggle, selectedIds }) {
  return <ResultDataTable ariaLabel="视频关键词" className="keyword-result-table" columns={columns}>{keywords.map((item) => { const selected = selectedIds.includes(item.id); const weight = Math.round(item.weight * 100); return <tr className={selected ? "is-selected" : ""} key={item.id}><td><ResultCheckbox checked={selected} label={`选择关键词 ${item.label}`} onChange={() => onToggle(item.id)} /></td><td><strong className="result-keyword">{item.label}</strong></td><td><span className="keyword-category">{item.group}</span></td><td><span className="weight-value">{weight}%<i aria-hidden="true"><b style={{ width: `${weight}%` }} /></i></span></td><td><span className="result-hit-count">{item.hits} 次</span></td><td><span className="evidence-links">{item.evidence.map((value) => <button aria-label={`${item.label} 的证据时间 ${value}`} key={value} onClick={() => onEvidence(item.label, value)} type="button">{value}</button>)}</span></td></tr>; })}</ResultDataTable>;
}
