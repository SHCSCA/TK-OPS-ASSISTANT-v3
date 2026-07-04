import { computed, onBeforeUnmount, ref, type Ref } from "vue";

type WorkspacePlaybackOptions = {
  hasTimeline: Ref<boolean>;
  playheadMs: Ref<number>;
  resolveDurationMs: () => number;
  setPlayheadMs: (positionMs: number) => void;
};

export function useWorkspacePlayback(options: WorkspacePlaybackOptions) {
  const isPlaying = ref(false);
  const playbackStartMs = ref(0);
  const playStartTimestamp = ref(0);
  let animationFrameHandle: number | null = null;

  const playProgress = computed(() => {
    const duration = options.resolveDurationMs();
    if (duration <= 0) return 0;
    return Math.min(100, Math.round((options.playheadMs.value / duration) * 100));
  });

  function seek(positionMs: number): void {
    const nextPositionMs = Math.max(0, Math.round(Number.isFinite(positionMs) ? positionMs : 0));
    options.setPlayheadMs(nextPositionMs);

    if (isPlaying.value) {
      playbackStartMs.value = nextPositionMs;
      playStartTimestamp.value = performance.now();
    }
  }

  function play(): void {
    if (isPlaying.value || !options.hasTimeline.value) return;

    const duration = options.resolveDurationMs();
    if (duration <= 0) return;

    if (options.playheadMs.value >= duration) {
      seek(0);
    }

    isPlaying.value = true;
    playbackStartMs.value = options.playheadMs.value;
    playStartTimestamp.value = performance.now();
    animationFrameHandle = requestAnimationFrame(playbackTick);
  }

  function pause(): void {
    isPlaying.value = false;
    if (animationFrameHandle !== null) {
      cancelAnimationFrame(animationFrameHandle);
      animationFrameHandle = null;
    }
  }

  function playbackTick(timestamp: number): void {
    if (!isPlaying.value) return;

    const elapsedMs = timestamp - playStartTimestamp.value;
    const duration = options.resolveDurationMs();
    const clamped = Math.min(playbackStartMs.value + elapsedMs, duration);

    options.setPlayheadMs(clamped);

    if (clamped >= duration) {
      isPlaying.value = false;
      animationFrameHandle = null;
      return;
    }

    animationFrameHandle = requestAnimationFrame(playbackTick);
  }

  onBeforeUnmount(() => {
    pause();
  });

  return {
    isPlaying,
    pause,
    play,
    playProgress,
    seek
  };
}
