import { emptyStateDefinitions } from "../data/emptyStateDefinitions.js";

export function resolvePageEmptyState(pageId, dataScenario, hasData = true) {
  if (dataScenario !== "empty" && hasData) return null;
  return emptyStateDefinitions[pageId] || null;
}
