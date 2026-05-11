import type { Paragraph } from "@/stores/voice-studio";

export type VoicePreviewRange = {
  endSec: number;
  index: number;
  startSec: number;
};

const MIN_SEGMENT_SECONDS = 0.5;

export function buildVoicePreviewRanges(
  paragraphs: Paragraph[] | null | undefined,
  audioDurationSec?: number | null
): VoicePreviewRange[] {
  const safeParagraphs = Array.isArray(paragraphs) ? paragraphs : [];
  const estimatedDurations = safeParagraphs.map((paragraph) =>
    Math.max(MIN_SEGMENT_SECONDS, Number(paragraph.estimatedDuration) || MIN_SEGMENT_SECONDS)
  );
  const estimatedTotal = estimatedDurations.reduce((sum, duration) => sum + duration, 0);
  if (estimatedTotal <= 0) {
    return [];
  }

  const targetTotal = typeof audioDurationSec === "number" && Number.isFinite(audioDurationSec) && audioDurationSec > 0
    ? audioDurationSec
    : estimatedTotal;
  const scale = targetTotal / estimatedTotal;
  let cursor = 0;

  return estimatedDurations.map((duration, index) => {
    const startSec = roundSeconds(cursor);
    cursor += duration * scale;
    const endSec = index === estimatedDurations.length - 1
      ? roundSeconds(targetTotal)
      : roundSeconds(cursor);
    return { endSec, index, startSec };
  });
}

export function formatPreviewTime(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  const minutes = Math.floor(safeSeconds / 60);
  const rest = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function roundSeconds(value: number): number {
  return Math.round(value * 100) / 100;
}
