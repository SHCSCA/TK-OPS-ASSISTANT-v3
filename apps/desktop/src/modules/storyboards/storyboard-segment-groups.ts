import type { ScriptWorkspaceTableRow } from "@/modules/scripts/script-document-view-model";
import type { StoryboardShotView } from "@/modules/storyboards/storyboard-document-view-model";

export type StoryboardShotTimeStatus = "ok" | "outside" | "unknown" | "missing_segment";

export type StoryboardShotGroupRow = {
  shot: StoryboardShotView;
  timeMessage: string;
  timeStatus: StoryboardShotTimeStatus;
};

export type StoryboardSegmentGroup = {
  rows: StoryboardShotGroupRow[];
  segmentId: string;
  segmentSummary: string;
  segmentTime: string;
};

type TimeRange = {
  end: number;
  start: number;
};

const TIME_RANGE_RE =
  /(\d+(?:\.\d+)?)\s*(?:s|秒)?\s*(?:-|–|—|~|至|到)\s*(\d+(?:\.\d+)?)\s*(?:s|秒)?/i;

export function buildStoryboardShotGroups(
  shots: StoryboardShotView[],
  scriptRows: ScriptWorkspaceTableRow[]
): StoryboardSegmentGroup[] {
  const scriptRowById = new Map(
    scriptRows.map((row) => [normalizeSegmentId(row.segmentId), row])
  );
  const groups: StoryboardSegmentGroup[] = [];
  const groupById = new Map<string, StoryboardSegmentGroup>();

  for (const shot of shots) {
    const segmentKey = normalizeSegmentId(shot.segmentId) || "未绑定段落";
    const scriptRow = scriptRowById.get(segmentKey);
    const group = ensureGroup(groups, groupById, segmentKey, scriptRow);
    const timeState = resolveShotTimeState(shot, scriptRow, segmentKey);
    group.rows.push({
      shot,
      timeMessage: timeState.message,
      timeStatus: timeState.status
    });
  }

  return groups;
}

function ensureGroup(
  groups: StoryboardSegmentGroup[],
  groupById: Map<string, StoryboardSegmentGroup>,
  segmentId: string,
  scriptRow: ScriptWorkspaceTableRow | undefined
): StoryboardSegmentGroup {
  const existing = groupById.get(segmentId);
  if (existing) {
    return existing;
  }

  const group: StoryboardSegmentGroup = {
    rows: [],
    segmentId,
    segmentSummary: scriptRow?.voiceover || scriptRow?.subtitle || scriptRow?.goal || "未找到脚本段落",
    segmentTime: scriptRow?.time || "未标注时间"
  };
  groups.push(group);
  groupById.set(segmentId, group);
  return group;
}

function resolveShotTimeState(
  shot: StoryboardShotView,
  scriptRow: ScriptWorkspaceTableRow | undefined,
  segmentId: string
): { message: string; status: StoryboardShotTimeStatus } {
  if (!scriptRow) {
    return {
      message: "未找到对应脚本段落",
      status: "missing_segment"
    };
  }

  const segmentRange = parseTimeRange(scriptRow.time);
  const shotRange = parseTimeRange(shot.time);
  if (!segmentRange || !shotRange) {
    return {
      message: "",
      status: "unknown"
    };
  }

  if (shotRange.start < segmentRange.start || shotRange.end > segmentRange.end) {
    return {
      message: `时间越界：${shot.time} 超出 ${segmentId} ${scriptRow.time}`,
      status: "outside"
    };
  }

  return {
    message: "",
    status: "ok"
  };
}

function parseTimeRange(value: string): TimeRange | null {
  const match = TIME_RANGE_RE.exec(value);
  if (!match) {
    return null;
  }

  const start = Number(match[1]);
  const end = Number(match[2]);
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return null;
  }

  return { end, start };
}

function normalizeSegmentId(value: string): string {
  return value.trim().toUpperCase();
}
