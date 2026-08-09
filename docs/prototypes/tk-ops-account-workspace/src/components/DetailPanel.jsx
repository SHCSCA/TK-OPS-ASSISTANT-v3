import { IconHistory, IconRefresh, IconSparkles, IconX } from "@tabler/icons-react";
import { GenerationNodeDetail } from "./generation-pipeline/GenerationNodeDetail.jsx";
import { GenerationPipeline } from "./generation-pipeline/GenerationPipeline.jsx";
import { BatchEntryDetail } from "./batch-production/BatchEntryDetail.jsx";
import { AssetDetail } from "./content-library/AssetDetail.jsx";
import { MediaToolTaskDetail } from "./media-toolbox/MediaToolTaskDetail.jsx";
import { ScriptVersionDetail } from "./script-topic/ScriptVersionDetail.jsx";
import { StoryboardSceneDetail } from "./storyboard-planning/StoryboardSceneDetail.jsx";

const detailTitles = {
  asset: "资产详情",
  "batch-entry": "内容队列项",
  "media-task": "媒体任务",
  "script-version": "脚本版本",
  "storyboard-scene": "镜头详情",
};

export function DetailPanel({ state }) {
  const detail = state.detail;
  if (!detail) return null;

  const item = detail.data;
  const specialTitle = detailTitles[detail.type];
  if (specialTitle) {
    const liveScript = detail.type === "script-version" ? state.creative.workflow.scripts.find((script) => script.id === item.id) || item : item;
    const liveScene = detail.type === "storyboard-scene" ? state.creative.selectedStoryboard?.scenes.find((scene) => scene.id === item.id) || item : item;
    const liveTask = detail.type === "media-task" ? state.media.tasks.find((task) => task.id === item.id) || item : item;
    const liveEntry = detail.type === "batch-entry" ? state.creative.production.entries.find((entry) => entry.id === item.id) || item : item;
    const liveAsset = detail.type === "asset" ? state.creative.library.allAssets.find((asset) => asset.id === item.id) || item : item;
    return (
      <PanelFrame item={item} onClose={() => state.setDetail(null)} title={specialTitle}>
        {detail.type === "script-version" ? <ScriptVersionDetail creative={state.creative} script={liveScript} /> : null}
        {detail.type === "storyboard-scene" ? <StoryboardSceneDetail creative={state.creative} scene={liveScene} /> : null}
        {detail.type === "media-task" ? <MediaToolTaskDetail media={state.media} task={liveTask} /> : null}
        {detail.type === "batch-entry" ? <BatchEntryDetail creative={state.creative} entry={liveEntry} navigate={state.navigate} /> : null}
        {detail.type === "asset" ? <AssetDetail asset={liveAsset} navigate={state.navigate} notify={state.notify} /> : null}
      </PanelFrame>
    );
  }

  const isException = detail.type === "exception";
  const isVariant = detail.type === "variant";
  const isNode = detail.type === "generation-step";
  const run = isNode ? detail.run : state.generationRuns[item.id];
  const title = isException ? "异常详情" : isVariant ? "成片预览" : isNode ? "AI 节点详情" : "批次详情";

  return (
    <PanelFrame item={item} onClose={() => state.setDetail(null)} title={title} footer={renderFooter()}>
      {isException ? <><div className={`detail-alert detail-alert--${item.tone}`}><strong>{item.title}</strong><p>{item.detail}</p></div><section className="detail-section"><h3>影响范围</h3><p>仅影响当前账号中的关联内容；其他账号和已完成阶段不受影响。</p></section><section className="detail-section"><h3>推荐恢复</h3><p>从最小失败范围重新执行，成功后自动刷新批次和任务状态。</p></section></> : null}
      {isVariant ? <><div className="video-preview-card"><IconSparkles size={24} /><span>9:16 成片预览</span><small>{item.version} · {item.duration}</small></div><section className="detail-section"><h3>当前版本</h3><p>{item.issue || "自动合成检查通过，可以确认成片。"}</p></section><section className="detail-section"><h3>版本动作</h3><button className="detail-action" onClick={() => state.notify("已切换到上一版本", "info")} type="button"><IconHistory size={17} />切换版本</button><button className="detail-action" onClick={() => state.notify("镜头级重生成已开始", "info")} type="button"><IconRefresh size={17} />重生成问题镜头</button></section></> : null}
      {!isException && !isVariant && !isNode ? <><div className="batch-detail-progress"><span><strong>{item.stage}</strong><small>{item.items} 条内容 · {run?.recipe || "账号默认配方"}</small></span><b>{item.progress}%</b></div><div className="progress-track progress-track--large"><i style={{ width: `${item.progress}%` }} /></div><section className="detail-section"><h3>AI 执行节点</h3><GenerationPipeline onOpenStep={(step) => state.setDetail({ type: "generation-step", data: step, run, batch: item })} onRetry={state.retryGenerationStep} run={run} /></section></> : null}
      {isNode ? <GenerationNodeDetail batchId={detail.batch.id} onBack={() => state.setDetail({ type: "batch", data: detail.batch })} onCancel={state.cancelGenerationStep} onFallback={state.fallbackGenerationStep} onRetry={state.retryGenerationStep} run={run} step={item} /> : null}
    </PanelFrame>
  );

  function renderFooter() {
    if (isNode) return null;
    if (isException) return <button className="primary-button" onClick={() => state.retryException(item.id)} type="button"><IconRefresh size={17} />{item.action}</button>;
    if (isVariant) return <button className="primary-button" onClick={() => state.notify("成片版本已确认")} type="button"><IconSparkles size={17} />确认成片</button>;
    return <button className="primary-button" onClick={() => state.notify("批次详情已刷新")} type="button"><IconRefresh size={17} />刷新状态</button>;
  }
}

function PanelFrame({ children, footer, item, onClose, title }) {
  return <aside className="detail-panel" aria-label="对象详情"><div className="detail-panel__header"><div><span>{title}</span><h2>{item.title || item.name}</h2></div><button className="icon-button" aria-label="关闭详情" onClick={onClose} type="button"><IconX size={18} /></button></div><div className="detail-panel__body">{children}</div>{footer ? <div className="detail-panel__footer">{footer}</div> : null}</aside>;
}
