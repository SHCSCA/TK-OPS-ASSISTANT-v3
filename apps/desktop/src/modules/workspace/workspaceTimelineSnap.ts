import type { WorkspaceTimelineClipDto } from "@/types/runtime";

export type TimelineSnapOptions = {
  movingClipId?: string | null;
  playheadMs?: number | null;
  timelineEndMs?: number | null;
};

export function buildSnapCandidates(
  clips: WorkspaceTimelineClipDto[],
  options: TimelineSnapOptions = {}
): number[] {
  const candidates = new Set<number>();

  candidates.add(0);
  addCandidate(candidates, options.playheadMs);
  addCandidate(candidates, options.timelineEndMs);

  for (const clip of clips) {
    if (clip.id === options.movingClipId) continue;

    addCandidate(candidates, clip.startMs);
    addCandidate(candidates, clip.startMs + clip.durationMs);
  }

  return [...candidates].sort((left, right) => left - right);
}

export function resolveTimelineSnap(desiredMs: number, candidates: number[], thresholdMs: number): number {
  const desired = normalizeTimelineMs(desiredMs);
  const threshold = Number.isFinite(thresholdMs) ? Math.max(0, Math.round(thresholdMs)) : 0;
  const nearest = candidates
    .map((candidate) => normalizeCandidate(candidate))
    .filter((candidate): candidate is number => candidate !== null)
    .map((candidate) => ({ candidate, distance: Math.abs(candidate - desired) }))
    .sort((left, right) => left.distance - right.distance || left.candidate - right.candidate)[0];

  if (!nearest || nearest.distance > threshold) return desired;

  return nearest.candidate;
}

function addCandidate(candidates: Set<number>, value: number | null | undefined): void {
  const candidate = normalizeCandidate(value);

  if (candidate === null) return;

  candidates.add(candidate);
}

function normalizeCandidate(value: number | null | undefined): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;

  return normalizeTimelineMs(value);
}

function normalizeTimelineMs(value: number): number {
  if (!Number.isFinite(value)) return 0;

  return Math.max(0, Math.round(value));
}
