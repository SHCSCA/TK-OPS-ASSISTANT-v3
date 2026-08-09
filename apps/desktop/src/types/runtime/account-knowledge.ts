export type PositioningStatus = "draft" | "active" | "archived";

export type PositioningVersionInput = {
  audience: Record<string, unknown>;
  contentPillars: string[];
  tone: Record<string, unknown>;
  prohibitedTopics: string[];
  publishingConstraints: Record<string, unknown>;
};

export type PositioningVersionSummaryDto = {
  version: number;
  status: PositioningStatus;
  summary: string;
  createdAt: string;
};

export type PositioningVersionDto = PositioningVersionSummaryDto & {
  id: string;
  accountId: string;
  audience: Record<string, unknown>;
  contentPillars: string[];
  tone: Record<string, unknown>;
  prohibitedTopics: string[];
  publishingConstraints: Record<string, unknown>;
  contentHash: string;
  activatedAt: string | null;
  revision: number;
};

export type PositioningDto = {
  accountId: string;
  activeVersion: number | null;
  versions: PositioningVersionSummaryDto[];
  revision: number;
};

export type KnowledgeKind =
  | "document"
  | "image"
  | "video"
  | "audio"
  | "text"
  | "reference";

export type KnowledgeSourceMode = "file" | "url" | "text";

export type KnowledgeSourceStatus =
  | "pending"
  | "indexing"
  | "ready"
  | "failed"
  | "stale"
  | "removed";

export type KnowledgeRulesInput = {
  inclusionRules: Record<string, unknown>;
  exclusionRules: Record<string, unknown>;
  citationPolicy: Record<string, unknown>;
};

export type KnowledgeDto = {
  accountId: string;
  rules: KnowledgeRulesInput;
  rulesVersion: number;
  sourceCounts: Record<string, number>;
  latestSnapshotId: string | null;
  readiness: Record<string, unknown>;
  revision: number;
};

type KnowledgeSourceInputBase = {
  kind: KnowledgeKind;
  title: string;
};

export type KnowledgeSourceInput =
  | KnowledgeSourceInputBase & {
      sourceMode: "file";
      controlledFileRef: string;
      url?: never;
      text?: never;
    }
  | KnowledgeSourceInputBase & {
      sourceMode: "url";
      controlledFileRef?: never;
      url: string;
      text?: never;
    }
  | KnowledgeSourceInputBase & {
      sourceMode: "text";
      controlledFileRef?: never;
      url?: never;
      text: string;
    };

export type KnowledgeSourceDto = {
  id: string;
  accountId: string;
  kind: KnowledgeKind;
  sourceMode: KnowledgeSourceMode;
  title: string;
  status: KnowledgeSourceStatus;
  controlledRef: string | null;
  sourceUrl: string | null;
  contentHash: string | null;
  indexedAt: string | null;
  removedAt: string | null;
  errorCode: string | null;
  logId: string | null;
  revision: number;
};

export type KnowledgeSourcePageDto = {
  items: KnowledgeSourceDto[];
  totalKnown: number | null;
};

export type KnowledgeSourceQuery = {
  kind?: KnowledgeKind;
  status?: KnowledgeSourceStatus;
  cursor?: string;
  limit?: number;
};

export type KnowledgeIndexInput = {
  sourceIds?: string[];
};

export type KnowledgeSourceEvidenceDto = {
  sourceId: string;
  contentHash: string;
  indexedRevision: number;
};

export type KnowledgeSnapshotInput = {
  sourceIds: string[];
  label?: string;
};

export type KnowledgeSnapshotDto = {
  id: string;
  accountId: string;
  label: string | null;
  sourceIds: string[];
  sourceEvidence: KnowledgeSourceEvidenceDto[];
  rulesVersion: number;
  contentHash: string;
  createdAt: string;
};

export type KnowledgeSnapshotPageDto = {
  items: KnowledgeSnapshotDto[];
  totalKnown: number | null;
};

export type KnowledgeSnapshotQuery = {
  cursor?: string;
  limit?: number;
};

export type BrandKitVersionInput = {
  colors: string[];
  fonts: string[];
  logoAssetRefs: string[];
  visualRules: Record<string, unknown>;
  voiceRules: Record<string, unknown>;
};

export type BrandKitVersionSummaryDto = {
  version: number;
  status: PositioningStatus;
  contentHash: string;
  createdAt: string;
};

export type ActiveBrandKitDto = {
  colors: string[];
  fonts: string[];
  logoAssetRefs: string[];
  visualRules: Record<string, unknown>;
  voiceRules: Record<string, unknown>;
};

export type BrandKitDto = {
  accountId: string;
  activeVersion: number | null;
  versions: BrandKitVersionSummaryDto[];
  active: ActiveBrandKitDto | null;
  revision: number;
};
