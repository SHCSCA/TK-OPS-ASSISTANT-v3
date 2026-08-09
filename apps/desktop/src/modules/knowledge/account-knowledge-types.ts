import type {
  BrandKitDto,
  KnowledgeDto,
  KnowledgeKind,
  KnowledgeSourceDto,
  KnowledgeSourceStatus,
  PositioningDto,
  PositioningVersionDto,
  PositioningVersionInput
} from "@/types/runtime/account-knowledge";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

export type KnowledgePageState =
  | "idle"
  | "loading"
  | "first_use"
  | "empty"
  | "waiting"
  | "error"
  | "ready";

export type KnowledgeCollectionState =
  | "loading"
  | "empty"
  | "filtered_empty"
  | "waiting"
  | "error"
  | "ready";

export type KnowledgeUiError = {
  message: string;
  errorCode: string | null;
  logId: string | null;
  requestId: string | null;
  retryable: boolean;
};

export type KnowledgeSourceFilters = {
  kind: KnowledgeKind | "";
  status: KnowledgeSourceStatus | "";
};

export type PositioningDraft = {
  audience: string;
  contentPillars: string;
  tone: string;
  prohibitedTopics: string;
  publishingConstraints: string;
};

export type PositioningDetailState =
  | "idle"
  | "loading"
  | "ready"
  | "error";

export type PositioningEditorMode =
  | { kind: "create" }
  | { kind: "fork"; sourceVersion: number };

export type KnowledgeRulesDraft = {
  inclusionRules: string;
  exclusionRules: string;
  citationPolicy: string;
};

export type KnowledgeSourceDraft = {
  mode: "text" | "url" | "file";
  title: string;
  text: string;
  url: string;
};

export type AccountKnowledgeCache = {
  accountId: string;
  pageState: KnowledgePageState;
  sourceState: KnowledgeCollectionState;
  positioning: PositioningDto | null;
  knowledge: KnowledgeDto | null;
  brandKit: BrandKitDto | null;
  sources: KnowledgeSourceDto[];
  sourceTotalKnown: number | null;
  sourceFilters: KnowledgeSourceFilters;
  positioningDraft: PositioningDraft;
  positioningEditorOpen: boolean;
  positioningEditorMode: PositioningEditorMode;
  positioningDirty: boolean;
  positioningDetailOpen: boolean;
  positioningDetailVersion: number | null;
  positioningDetailState: PositioningDetailState;
  positioningDetail: PositioningVersionDto | null;
  positioningDetailError: KnowledgeUiError | null;
  rulesDraft: KnowledgeRulesDraft;
  rulesBaseline: KnowledgeRulesDraft;
  rulesDirty: boolean;
  sourceDraft: KnowledgeSourceDraft;
  sourceEditorOpen: boolean;
  sourceDirty: boolean;
  indexTask: RuntimeTaskDto | null;
  indexTaskId: string | null;
  error: KnowledgeUiError | null;
  feedback: string | null;
  busyKey: string | null;
};

export function emptyPositioningDraft(): PositioningDraft {
  return {
    audience: "",
    contentPillars: "",
    tone: "",
    prohibitedTopics: "",
    publishingConstraints: ""
  };
}

export function emptyKnowledgeSourceDraft(): KnowledgeSourceDraft {
  return {
    mode: "text",
    title: "",
    text: "",
    url: ""
  };
}

export function toPositioningInput(
  draft: PositioningDraft
): PositioningVersionInput {
  return {
    audience: { description: draft.audience.trim() },
    contentPillars: splitLines(draft.contentPillars),
    tone: { description: draft.tone.trim() },
    prohibitedTopics: splitLines(draft.prohibitedTopics),
    publishingConstraints: draft.publishingConstraints.trim()
      ? { description: draft.publishingConstraints.trim() }
      : {}
  };
}

export function splitLines(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(/\r?\n|[,，]/)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
}
