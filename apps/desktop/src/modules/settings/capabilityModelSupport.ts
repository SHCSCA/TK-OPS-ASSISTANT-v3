import type { AICapabilityModelOption, AIModelCatalogItem } from "@/types/runtime";

type SupportModel = Pick<AICapabilityModelOption, "provider" | "modelId" | "capabilityTypes" | "displayName">;

export function isModelAllowedBySupport(
  providerId: string,
  modelId: string,
  supportModels: SupportModel[]
): boolean {
  return supportModels.some(
    (item) => item.provider === providerId && modelIdMatchesBinding(item.modelId, modelId)
  );
}

export function findSupportedModelOption(
  providerId: string,
  modelId: string,
  supportModels: SupportModel[]
): SupportModel | null {
  return (
    supportModels.find(
      (item) => item.provider === providerId && modelIdMatchesBinding(item.modelId, modelId)
    ) ?? null
  );
}

export function filterModelsBySupport(
  providerId: string,
  loadedModels: AIModelCatalogItem[],
  supportModels: SupportModel[]
): AIModelCatalogItem[] {
  const providerSupportModels = supportModels.filter((item) => item.provider === providerId);
  if (providerSupportModels.length === 0) {
    return loadedModels;
  }
  return loadedModels.filter((model) =>
    providerSupportModels.some(
      (item) =>
        modelIdMatchesBinding(model.modelId, item.modelId) ||
        modelIdMatchesBinding(item.modelId, model.modelId)
    )
  );
}

export function modelIdMatchesBinding(supportedModelId: string, requestedModelId: string): boolean {
  const supportedToken = normalizeModelAliasToken(supportedModelId);
  const requestedToken = normalizeModelAliasToken(requestedModelId);
  if (!supportedToken || !requestedToken) {
    return false;
  }
  return supportedToken === requestedToken || isVersionedModelSuccessor(supportedToken, requestedToken);
}

function isVersionedModelSuccessor(candidateToken: string, requestedToken: string): boolean {
  const prefix = `${requestedToken}-`;
  if (!candidateToken.startsWith(prefix)) {
    return false;
  }
  const suffix = candidateToken.slice(prefix.length);
  const firstSegment = suffix.split("-", 1)[0] ?? "";
  return /^\d{6,}$/.test(firstSegment);
}

function normalizeModelAliasToken(value: string): string {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
    .join("-");
}
