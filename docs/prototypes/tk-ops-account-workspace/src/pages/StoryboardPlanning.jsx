import { IconArrowLeft, IconCheck, IconPlayerPlay, IconRefresh, IconSparkles } from "@tabler/icons-react";
import { CreativeChainHeader } from "../components/creative-chain/CreativeChainHeader.jsx";
import { ProductionHandoffDialog } from "../components/storyboard-planning/ProductionHandoffDialog.jsx";
import { ScriptOutlineRail } from "../components/storyboard-planning/ScriptOutlineRail.jsx";
import { StoryboardSceneList } from "../components/storyboard-planning/StoryboardSceneList.jsx";
import { canConfirmStoryboard, canEnterStoryboard, hasStoryboardRevisionMismatch } from "../data/creativeWorkflow.js";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function StoryboardPlanning({ state }) {
  const creative = state.creative;
  const item = creative.selectedContentItem;
  const script = creative.selectedScript;
  const board = creative.selectedStoryboard;
  const mismatch = hasStoryboardRevisionMismatch(script, board);
  const failedScene = board?.scenes.find((scene) => scene.status === "failed");
  const storyboardRoute = state.aiSettings.routeStatuses.storyboard;
  const emptyState = resolvePageEmptyState("storyboard", state.dataScenario, Boolean(script));
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.navigate("scripts")} /></div>;

  let action = <button className="primary-button" onClick={() => state.navigate("scripts")} type="button"><IconArrowLeft size={16} />返回脚本</button>;
  if (canEnterStoryboard(script) && !board) action = storyboardRoute.ready ? <button className="primary-button" onClick={() => creative.generateStoryboard(script)} type="button"><IconSparkles size={16} />AI 生成分镜</button> : <button className="primary-button" onClick={() => { state.navigate("settings"); state.notify(`分镜能力不可用：${storyboardRoute.reason}`, "danger"); }} type="button">配置分镜模型</button>;
  if (board && mismatch) action = <button className="primary-button" onClick={() => creative.generateStoryboard(script)} type="button"><IconRefresh size={16} />同步脚本并重建</button>;
  if (failedScene && !mismatch) action = <button className="primary-button" onClick={() => { creative.selectScene(failedScene.id); state.setDetail({ type: "storyboard-scene", data: failedScene }); }} type="button">处理异常镜头</button>;
  if (board && !mismatch && !failedScene && canConfirmStoryboard(board)) action = <button className="primary-button" onClick={creative.confirmStoryboard} type="button"><IconCheck size={16} />确认分镜</button>;
  if (board?.status === "confirmed" && !mismatch) action = <button className="primary-button" onClick={creative.production.openHandoff} type="button"><IconPlayerPlay size={16} />进入生产</button>;

  return (
    <div className="page-stack page-enter">
      <CreativeChainHeader action={action} contentItem={item} stages={creative.stages} />
      <div className="creative-workspace creative-workspace--storyboard">
        <ScriptOutlineRail script={script} storyboard={board} />
        <section className="workflow-main">
          <header className="workspace-card-header"><div><span className="section-kicker">镜头列表</span><h2>{board ? `${board.scenes.length} 个镜头` : "等待生成"}</h2></div>{mismatch ? <span className="status-pill status-pill--warning">脚本版本不一致</span> : board ? <span className={`status-pill status-pill--${board.status === "confirmed" ? "ready" : "brand"}`}>{board.status === "confirmed" ? "已确认" : "待确认"}</span> : null}</header>
          <StoryboardSceneList creative={creative} onOpenScene={(scene) => state.setDetail({ type: "storyboard-scene", data: scene })} />
        </section>
      </div>
      <ProductionHandoffDialog creative={creative} />
    </div>
  );
}
