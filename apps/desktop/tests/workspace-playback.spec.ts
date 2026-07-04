import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkspacePlayback } from "@/modules/workspace/useWorkspacePlayback";

describe("M05 预览播放控制", () => {
  let animationCallbacks: FrameRequestCallback[] = [];

  beforeEach(() => {
    animationCallbacks = [];
    vi.spyOn(performance, "now").mockReturnValue(1000);
    vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => {
      animationCallbacks.push(callback);
      return animationCallbacks.length;
    }));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("播放中定位片段起点会重置播放基准，下一帧不会跳回旧进度", async () => {
    const wrapper = mount(playbackHarness());

    wrapper.vm.play();
    await nextTick();
    expect(wrapper.vm.playheadMs).toBe(1000);

    wrapper.vm.seek(5200);
    animationCallbacks.at(-1)?.(1300);
    await nextTick();

    expect(wrapper.vm.playheadMs).toBe(5500);
  });
});

function playbackHarness() {
  return defineComponent({
    setup() {
      const hasTimeline = ref(true);
      const playheadMs = ref(1000);
      const playback = useWorkspacePlayback({
        hasTimeline,
        playheadMs,
        resolveDurationMs: () => 10_000,
        setPlayheadMs: (positionMs) => {
          playheadMs.value = positionMs;
        }
      });

      return {
        ...playback,
        playheadMs
      };
    },
    template: "<div />"
  });
}
