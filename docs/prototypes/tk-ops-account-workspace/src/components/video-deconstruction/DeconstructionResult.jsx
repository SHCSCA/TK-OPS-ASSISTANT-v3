import { useEffect, useState } from "react";
import { IconFileText, IconKey, IconKeyframe, IconListTree } from "@tabler/icons-react";
import { KeyframeResult } from "./KeyframeResult.jsx";
import { KeywordResult } from "./KeywordResult.jsx";
import { ScriptSegmentsResult } from "./ScriptSegmentsResult.jsx";
import { StructureResult } from "./StructureResult.jsx";

const tabs = [
  { id: "script", label: "脚本文案", icon: IconFileText },
  { id: "keywords", label: "关键词", icon: IconKey },
  { id: "keyframes", label: "关键帧", icon: IconKeyframe },
  { id: "structure", label: "内容结构", icon: IconListTree },
];

export function DeconstructionResult({ item, onApply, onEvidence, onRetry }) {
  const [tab, setTab] = useState("script");
  const [selection, setSelection] = useState(() => buildSelection(item));
  useEffect(() => setSelection(buildSelection(item)), [item.id]);
  if (item.status === "running") return <div className="recovery-card"><strong>正在分析视频内容</strong><p>脚本、关键词、关键帧和结构证据会按阶段出现，可随时返回任务列表。</p></div>;
  if (item.status !== "completed") return <div className="recovery-card"><strong>{item.failureType === "provider" ? "AI Provider 暂不可用" : item.failureType === "ffprobe" ? "媒体探针不可用" : "来源无法读取"}</strong><p>{item.error}</p></div>;
  return <div className="deconstruction-result"><div className="result-tabs" role="tablist">{tabs.map(({ id, label, icon: Icon }) => <button aria-controls={`deconstruction-panel-${id}`} aria-selected={tab === id} className={tab === id ? "is-active" : ""} id={`deconstruction-tab-${id}`} key={id} onClick={() => setTab(id)} role="tab" type="button"><Icon size={14} />{label}</button>)}</div><div aria-labelledby={`deconstruction-tab-${tab}`} className="result-panel" id={`deconstruction-panel-${tab}`} role="tabpanel">{tab === "script" ? <ScriptSegmentsResult onToggle={(id) => toggle("scriptSegmentIds", id)} segments={item.result.scriptSegments} selectedIds={selection.scriptSegmentIds} /> : null}{tab === "keywords" ? <KeywordResult keywords={item.result.keywords} onEvidence={onEvidence} onToggle={(id) => toggle("keywordIds", id)} selectedIds={selection.keywordIds} /> : null}{tab === "keyframes" ? <KeyframeResult frames={item.result.keyframes} onRetry={onRetry} onToggle={(id) => toggle("keyframeIds", id)} selectedIds={selection.keyframeIds} /> : null}{tab === "structure" ? <StructureResult onToggle={(id) => toggle("structureIds", id)} segments={item.result.structureSegments} selectedIds={selection.structureIds} summary={item.result.structureSummary} /> : null}</div><footer className="result-actions"><span>已选 {selection.scriptSegmentIds.length} 段脚本 · {selection.keywordIds.length} 个关键词 · {selection.keyframeIds.length} 个关键帧 · {selection.structureIds.length} 段结构</span><button className="primary-button" onClick={() => onApply(selection)} type="button">应用结果</button></footer></div>;

  function toggle(field, id) {
    setSelection((current) => ({ ...current, [field]: current[field].includes(id) ? current[field].filter((value) => value !== id) : [...current[field], id] }));
  }
}

function buildSelection(item) {
  return {
    keywordIds: item.result.keywords.slice(0, 2).map((value) => value.id),
    keyframeIds: item.result.keyframes.filter((value) => value.imageRef).map((value) => value.id),
    scriptSegmentIds: item.result.scriptSegments.map((value) => value.id),
    structureIds: item.result.structureSegments.slice(0, 1).map((value) => value.id),
  };
}
