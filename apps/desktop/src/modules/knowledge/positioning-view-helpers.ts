import type { PositioningVersionDto } from "@/types/runtime/account-knowledge";

import type { PositioningDraft } from "./account-knowledge-types";

export function toPositioningDraft(
  dto: PositioningVersionDto
): PositioningDraft {
  return {
    audience: objectDescription(dto.audience),
    contentPillars: dto.contentPillars.join("\n"),
    tone: objectDescription(dto.tone),
    prohibitedTopics: dto.prohibitedTopics.join("\n"),
    publishingConstraints: objectDescription(
      dto.publishingConstraints,
      true
    )
  };
}

export function objectDescription(
  value: Record<string, unknown>,
  fallbackToJson = false
): string {
  const description = value.description;
  if (typeof description === "string" && description.trim()) {
    return description.trim();
  }
  if (!fallbackToJson || Object.keys(value).length === 0) return "";
  return JSON.stringify(value, null, 2);
}

export function positioningToneTags(
  value: Record<string, unknown>
): string[] {
  return Array.from(
    new Set(
      objectDescription(value)
        .split(/[、，,;；\n]/u)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  ).slice(0, 5);
}

export function positioningHashPreview(value: string): string {
  if (value.length <= 18) return value;
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}
