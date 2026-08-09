import { useMemo, useState } from "react";
import { cloneCreativeWorkflows } from "../data/creativeWorkflow.js";
import { useAssetLibraryState } from "./useAssetLibraryState.js";
import { useContentItemState } from "./useContentItemState.js";
import { useDeconstructionState } from "./useDeconstructionState.js";
import { useProductionHandoffState } from "./useProductionHandoffState.js";

export function useCreativeWorkflowState(activeAccountId, notify, navigate) {
  const [workflows, setWorkflows] = useState(cloneCreativeWorkflows);
  const emptyWorkflow = useMemo(() => createEmptyWorkflow(activeAccountId), [activeAccountId]);
  const workflow = workflows[activeAccountId] || emptyWorkflow;

  function updateActiveWorkflow(updater) {
    setWorkflows((current) => {
      const base = current[activeAccountId] || createEmptyWorkflow(activeAccountId);
      return { ...current, [activeAccountId]: updater(base) };
    });
  }

  const content = useContentItemState({ activeAccountId, navigate, notify, updateActiveWorkflow, workflow });
  const production = useProductionHandoffState({ activeAccountId, content, navigate, notify, updateActiveWorkflow, workflow });
  const deconstruction = useDeconstructionState({ activeAccountId, content, navigate, notify, updateActiveWorkflow, workflow });
  const library = useAssetLibraryState(activeAccountId, workflow);

  return {
    ...content,
    ...deconstruction,
    ...production,
    content,
    deconstruction,
    library,
    production,
    workflow,
  };
}

function createEmptyWorkflow(accountId) {
  return {
    assets: [],
    batches: [],
    contentItems: [],
    deconstructions: [],
    entries: [],
    scripts: [],
    selectedBatchId: null,
    selectedContentItemId: null,
    selectedDeconstructionId: null,
    selectedSceneId: null,
    storyboards: [],
    variants: [],
    accountId,
  };
}
