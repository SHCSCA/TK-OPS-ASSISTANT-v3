import { readonly, ref, toValue, type MaybeRefOrGetter, type Ref } from "vue";

import { clampTimelineMs, clientXToTimelineMs, type TimelineRectLike } from "./workspaceTimelineGeometry";
import { resolveTimelineSnap } from "./workspaceTimelineSnap";

export type WorkspaceTimelineDragRect = TimelineRectLike;

export type WorkspaceTimelineDragClip = {
  id: string;
  trackId: string;
  startMs: number;
  durationMs: number;
  inPointMs?: number;
};

export type WorkspaceTimelineMovePreview = {
  gesture: "move";
  clipId: string;
  trackId: string;
  startMs: number;
  durationMs: number;
};

export type WorkspaceTimelineTrimEdge = "left" | "right";

export type WorkspaceTimelineTrimPreview = {
  gesture: "trim";
  clipId: string;
  trackId: string;
  edge: WorkspaceTimelineTrimEdge;
  startMs: number;
  durationMs: number;
  inPointMs: number;
};

export type WorkspaceTimelineDragPreview = WorkspaceTimelineMovePreview | WorkspaceTimelineTrimPreview;

export type WorkspaceTimelineDragOptions = {
  durationMs: MaybeRefOrGetter<number>;
  snapCandidates?: MaybeRefOrGetter<number[]>;
  snapThresholdMs?: MaybeRefOrGetter<number>;
  minDurationMs?: MaybeRefOrGetter<number>;
};

export type WorkspaceTimelineMoveDragInput = {
  clip: WorkspaceTimelineDragClip;
  clientX: number;
  rect: WorkspaceTimelineDragRect;
};

export type WorkspaceTimelineTrimDragInput = WorkspaceTimelineMoveDragInput & {
  edge: WorkspaceTimelineTrimEdge;
};

export type WorkspaceTimelineDragUpdateInput = {
  clientX: number;
  rect: WorkspaceTimelineDragRect;
};

type ActiveDragState =
  | {
      gesture: "move";
      clip: Required<WorkspaceTimelineDragClip>;
      pointerOffsetMs: number;
    }
  | {
      gesture: "trim";
      clip: Required<WorkspaceTimelineDragClip>;
      edge: WorkspaceTimelineTrimEdge;
    };

export function useWorkspaceTimelineDrag(options: WorkspaceTimelineDragOptions): {
  dragPreview: Readonly<Ref<WorkspaceTimelineDragPreview | null>>;
  startMoveDrag: (input: WorkspaceTimelineMoveDragInput) => WorkspaceTimelineMovePreview;
  startTrimDrag: (input: WorkspaceTimelineTrimDragInput) => WorkspaceTimelineTrimPreview;
  updateDrag: (input: WorkspaceTimelineDragUpdateInput) => WorkspaceTimelineDragPreview | null;
  finishDrag: () => WorkspaceTimelineDragPreview | null;
  cancelDrag: () => WorkspaceTimelineDragPreview | null;
} {
  const activeDrag = ref<ActiveDragState | null>(null);
  const dragPreview = ref<WorkspaceTimelineDragPreview | null>(null);

  function startMoveDrag(input: WorkspaceTimelineMoveDragInput): WorkspaceTimelineMovePreview {
    const clip = normalizeClip(input.clip);
    const pointerMs = clientXToTimelineMs(input.clientX, input.rect, getDurationMs());

    activeDrag.value = {
      gesture: "move",
      clip,
      pointerOffsetMs: pointerMs - clip.startMs
    };
    dragPreview.value = buildMovePreview(clip, clip.startMs);

    return dragPreview.value;
  }

  function startTrimDrag(input: WorkspaceTimelineTrimDragInput): WorkspaceTimelineTrimPreview {
    const clip = normalizeClip(input.clip);

    activeDrag.value = {
      gesture: "trim",
      clip,
      edge: input.edge
    };
    dragPreview.value = buildTrimPreview(clip, input.edge, clip.startMs, clip.durationMs, clip.inPointMs);

    return dragPreview.value;
  }

  function updateDrag(input: WorkspaceTimelineDragUpdateInput): WorkspaceTimelineDragPreview | null {
    const active = activeDrag.value;

    if (!active) return null;

    const pointerMs = clientXToTimelineMs(input.clientX, input.rect, getDurationMs());

    dragPreview.value = active.gesture === "move" ? updateMove(active, pointerMs) : updateTrim(active, pointerMs);

    return dragPreview.value;
  }

  function finishDrag(): WorkspaceTimelineDragPreview | null {
    const preview = dragPreview.value;

    activeDrag.value = null;
    dragPreview.value = null;

    return preview;
  }

  function cancelDrag(): WorkspaceTimelineDragPreview | null {
    const preview = dragPreview.value;

    activeDrag.value = null;
    dragPreview.value = null;

    return preview;
  }

  function updateMove(active: Extract<ActiveDragState, { gesture: "move" }>, pointerMs: number): WorkspaceTimelineMovePreview {
    const duration = getDurationMs();
    const maxStartMs = Math.max(0, duration - active.clip.durationMs);
    const desiredStartMs = pointerMs - active.pointerOffsetMs;
    const snappedStartMs = snapTimelineMs(desiredStartMs);
    const startMs = Math.min(maxStartMs, clampTimelineMs(snappedStartMs, duration));

    return buildMovePreview(active.clip, startMs);
  }

  function updateTrim(active: Extract<ActiveDragState, { gesture: "trim" }>, pointerMs: number): WorkspaceTimelineTrimPreview {
    const duration = getDurationMs();
    const minDuration = getMinDurationMs();
    const clipEndMs = active.clip.startMs + active.clip.durationMs;
    const snappedMs = snapTimelineMs(pointerMs);

    if (active.edge === "left") {
      const maxStartMs = Math.max(active.clip.startMs, clipEndMs - minDuration);
      const startMs = Math.min(maxStartMs, clampTimelineMs(snappedMs, duration));
      const durationMs = Math.max(minDuration, clipEndMs - startMs);
      const inPointMs = Math.max(0, active.clip.inPointMs + (startMs - active.clip.startMs));

      return buildTrimPreview(active.clip, "left", startMs, durationMs, inPointMs);
    }

    const minEndMs = active.clip.startMs + minDuration;
    const endMs = Math.max(minEndMs, clampTimelineMs(snappedMs, duration));
    const durationMs = endMs - active.clip.startMs;

    return buildTrimPreview(active.clip, "right", active.clip.startMs, durationMs, active.clip.inPointMs);
  }

  function getDurationMs(): number {
    return Math.max(0, Math.round(toValue(options.durationMs)));
  }

  function getMinDurationMs(): number {
    const configured = options.minDurationMs === undefined ? 500 : toValue(options.minDurationMs);

    return Math.max(1, Math.round(configured));
  }

  function snapTimelineMs(value: number): number {
    return resolveTimelineSnap(value, toValue(options.snapCandidates) ?? [], toValue(options.snapThresholdMs) ?? 0);
  }

  return {
    dragPreview: readonly(dragPreview),
    startMoveDrag,
    startTrimDrag,
    updateDrag,
    finishDrag,
    cancelDrag
  };
}

function normalizeClip(clip: WorkspaceTimelineDragClip): Required<WorkspaceTimelineDragClip> {
  return {
    id: clip.id,
    trackId: clip.trackId,
    startMs: Math.max(0, Math.round(clip.startMs)),
    durationMs: Math.max(0, Math.round(clip.durationMs)),
    inPointMs: Math.max(0, Math.round(clip.inPointMs ?? 0))
  };
}

function buildMovePreview(clip: Required<WorkspaceTimelineDragClip>, startMs: number): WorkspaceTimelineMovePreview {
  return {
    gesture: "move",
    clipId: clip.id,
    trackId: clip.trackId,
    startMs,
    durationMs: clip.durationMs
  };
}

function buildTrimPreview(
  clip: Required<WorkspaceTimelineDragClip>,
  edge: WorkspaceTimelineTrimEdge,
  startMs: number,
  durationMs: number,
  inPointMs: number
): WorkspaceTimelineTrimPreview {
  return {
    gesture: "trim",
    clipId: clip.id,
    trackId: clip.trackId,
    edge,
    startMs,
    durationMs,
    inPointMs
  };
}
