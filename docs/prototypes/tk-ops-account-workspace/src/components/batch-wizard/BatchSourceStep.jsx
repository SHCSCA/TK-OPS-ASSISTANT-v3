import { IconFileText, IconMovie, IconPhoto, IconSparkles } from "@tabler/icons-react";
import { prototypeConfig } from "../../config/prototypeConfig.js";
import { splitFixedScript } from "./batchWizardHelpers.js";

const sourceOptions = [
  { id: "confirmed", label: "已确认内容", detail: "消费已完成脚本与分镜的内容对象", Icon: IconMovie },
  { id: "topic", label: "AI 主题", detail: "从当前定位与知识生成选题", Icon: IconSparkles },
  { id: "script", label: "固定脚本", detail: "按规则拆为多条，跳过脚本生成", Icon: IconFileText },
  { id: "assets", label: "已有素材", detail: "先分析当前账号图片或视频，再规划视觉", Icon: IconPhoto },
];

export function BatchSourceStep({ assets, canImageToVideo, form, update }) {
  const segments = splitFixedScript(form.fixedScript, form.splitMode);
  function toggleAsset(assetId) {
    update("assetIds", form.assetIds.includes(assetId) ? form.assetIds.filter((id) => id !== assetId) : [...form.assetIds, assetId]);
  }
  return <div className="wizard-stack"><div className="source-mode-grid">{sourceOptions.map(({ id, label, detail, Icon }) => <button className={form.mode === id ? "is-active" : ""} key={id} onClick={() => update("mode", id)} type="button"><Icon size={22} /><strong>{label}</strong><small>{detail}</small></button>)}</div>{form.mode === "script" ? <div className="fixed-script-panel"><label className="field field--wide">固定脚本<textarea onChange={(event) => update("fixedScript", event.target.value)} placeholder="粘贴脚本，可按段落、行或句子拆成多条内容。" rows="6" value={form.fixedScript} /></label><label className="field">拆分方式<select onChange={(event) => update("splitMode", event.target.value)} value={form.splitMode}>{prototypeConfig.production.scriptSplitModes.map((mode) => <option key={mode.id} value={mode.id}>{mode.label}</option>)}</select></label><div className="script-split-preview"><small>预计生成</small><strong>{segments.length} 条</strong><span>{prototypeConfig.production.scriptSplitModes.find((mode) => mode.id === form.splitMode)?.hint}</span></div>{segments.length ? <ol className="script-segment-list">{segments.slice(0, 3).map((segment, index) => <li key={`${segment}-${index}`}><i>{index + 1}</i><span>{segment}</span></li>)}</ol> : null}</div> : null}{form.mode === "assets" ? <div className="asset-source-panel"><header><div><strong>账号素材分析</strong><small>只读取当前账号内容库，结果进入“视觉规划”节点。</small></div><label className={`image-to-video-option ${canImageToVideo ? "" : "is-disabled"}`}><input checked={form.useImageToVideo} disabled={!canImageToVideo} onChange={(event) => update("useImageToVideo", event.target.checked)} type="checkbox" /><span><strong>生成动态镜头</strong><small>{canImageToVideo ? "使用当前配方的图生视频能力" : "请在第三步选择图生视频配方"}</small></span></label></header><div>{assets.length ? assets.map((asset) => <label className={form.assetIds.includes(asset.id) ? "is-selected" : ""} key={asset.id}><input checked={form.assetIds.includes(asset.id)} onChange={() => toggleAsset(asset.id)} type="checkbox" /><span><strong>{asset.title}</strong><small>{asset.kind} · {asset.matchReason}</small></span></label>) : <p>当前账号没有可用视频或图片素材。</p>}</div></div> : null}</div>;
}

export function getSourceLabel(mode) {
  return sourceOptions.find((item) => item.id === mode)?.label || "AI 主题";
}
