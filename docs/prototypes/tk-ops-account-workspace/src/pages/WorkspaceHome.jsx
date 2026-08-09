import { BatchTable } from "../components/BatchTable.jsx";
import { ExceptionList } from "../components/ExceptionList.jsx";
import { StageFlow } from "../components/StageFlow.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function WorkspaceHome({ state }) {
  const emptyState = resolvePageEmptyState("workspace", state.dataScenario, state.workspace.batches.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={(action) => action === "new-topic" ? (state.navigate("scripts"), state.creative.openTopicDialog()) : state.setBatchDialogOpen(true)} /></div>;
  return (
    <div className="workspace-home page-enter">
      <StageFlow
        activeStage={state.stageFilter}
        batches={state.workspace.batches}
        onSelect={state.setStageFilter}
      />
      <BatchTable
        batches={state.workspace.batches}
        stageFilter={state.stageFilter}
        onOpen={state.setDetail}
        onRetry={state.retryBatch}
      />
      <ExceptionList
        exceptions={state.workspace.exceptions}
        onOpen={state.setDetail}
        onRetry={state.retryException}
      />
    </div>
  );
}
