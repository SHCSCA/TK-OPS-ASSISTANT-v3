import { PageSection } from "../components/PageSection.jsx";
import { MediaToolGrid } from "../components/media-toolbox/MediaToolGrid.jsx";
import { MediaToolTaskList } from "../components/media-toolbox/MediaToolTaskList.jsx";
import { MediaToolWizard } from "../components/media-toolbox/MediaToolWizard.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function MediaToolbox({ state }) {
  const emptyState = resolvePageEmptyState("toolbox", state.dataScenario, state.media.tasks.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.media.openTool("download")} /><MediaToolWizard media={state.media} /></div>;
  return <div className="page-stack page-enter"><PageSection title="媒体工具箱" meta="轻量处理任务；输出只进入当前账号内容库"><MediaToolGrid onOpen={state.media.openTool} /></PageSection><PageSection title="最近任务" meta={`${state.media.tasks.length} 个演示任务`}><MediaToolTaskList media={state.media} onOpenTask={(task) => state.setDetail({ type: "media-task", data: task })} /></PageSection><MediaToolWizard media={state.media} /></div>;
}
