import { IconArrowRight, IconCheck, IconFileText, IconSparkles } from "@tabler/icons-react";
import { CreativeChainHeader } from "../components/creative-chain/CreativeChainHeader.jsx";
import { ScriptWorkspace } from "../components/script-topic/ScriptWorkspace.jsx";
import { TopicBriefRail } from "../components/script-topic/TopicBriefRail.jsx";
import { TopicCreateDialog } from "../components/script-topic/TopicCreateDialog.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function ScriptTopicCenter({ state }) {
  const creative = state.creative;
  const item = creative.selectedContentItem;
  const script = creative.selectedScript;
  const adopted = script?.status === "adopted" && script.adoptedRevision === script.revision;
  const pillars = state.workspace.strategy?.pillars || ["工具拆解", "效率实验", "真实复盘"];
  const scriptRoute = state.aiSettings.routeStatuses["script-generate"];
  const emptyState = resolvePageEmptyState("scripts", state.dataScenario, creative.workflow.contentItems.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => creative.openTopicDialog()} /><TopicCreateDialog creative={creative} pillars={pillars} /></div>;

  let action = <button className="primary-button" onClick={() => creative.openTopicDialog()} type="button"><IconFileText size={16} />新建选题</button>;
  if (item && !script) action = scriptRoute.ready ? <button className="primary-button" onClick={() => creative.generateScript()} type="button"><IconSparkles size={16} />AI 生成脚本</button> : <button className="primary-button" onClick={() => { state.navigate("settings"); state.notify(`脚本能力不可用：${scriptRoute.reason}`, "danger"); }} type="button">配置脚本模型</button>;
  if (script && !adopted) action = <button className="primary-button" onClick={() => creative.adoptScript(script.id)} type="button"><IconCheck size={16} />采用脚本</button>;
  if (script && adopted) action = <button className="primary-button" onClick={() => creative.enterStoryboard(script)} type="button">进入分镜<IconArrowRight size={16} /></button>;

  return (
    <div className="page-stack page-enter">
      <CreativeChainHeader action={action} contentItem={item} onOpenTopic={() => creative.openTopicDialog()} stages={creative.stages} />
      <div className="creative-workspace"><TopicBriefRail creative={creative} /><ScriptWorkspace creative={creative} onOpenVersion={(value) => state.setDetail({ type: "script-version", data: value })} /></div>
      <TopicCreateDialog creative={creative} pillars={pillars} />
    </div>
  );
}
