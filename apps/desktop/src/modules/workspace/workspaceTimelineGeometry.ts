export type TimelineRectLike = {
  left: number;
  width: number;
};

export function clampTimelineMs(value: number, durationMs: number): number {
  const duration = normalizeDurationMs(durationMs);

  if (duration <= 0 || !Number.isFinite(value)) return 0;

  return Math.min(duration, Math.max(0, Math.round(value)));
}

export function msToPercent(value: number, durationMs: number): number {
  const duration = normalizeDurationMs(durationMs);

  if (duration <= 0) return 0;

  return roundTimelineNumber((clampTimelineMs(value, duration) / duration) * 100);
}

export function percentToMs(percent: number, durationMs: number): number {
  const duration = normalizeDurationMs(durationMs);

  if (duration <= 0 || !Number.isFinite(percent)) return 0;

  const clampedPercent = Math.min(100, Math.max(0, percent));

  return clampTimelineMs((clampedPercent / 100) * duration, duration);
}

export function clientXToTimelineMs(clientX: number, rect: TimelineRectLike, durationMs: number): number {
  const width = Number.isFinite(rect.width) ? rect.width : 0;

  if (!Number.isFinite(clientX) || !Number.isFinite(rect.left) || width <= 0) return 0;

  const percent = ((clientX - rect.left) / width) * 100;

  return percentToMs(percent, durationMs);
}

function normalizeDurationMs(durationMs: number): number {
  if (!Number.isFinite(durationMs)) return 0;

  return Math.max(0, Math.round(durationMs));
}

function roundTimelineNumber(value: number): number {
  return Number(value.toFixed(3));
}
