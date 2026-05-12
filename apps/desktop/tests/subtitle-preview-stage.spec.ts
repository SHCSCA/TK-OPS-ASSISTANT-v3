import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SubtitlePreviewStage from "@/modules/subtitles/SubtitlePreviewStage.vue";

describe("SubtitlePreviewStage", () => {
  it("uses a draggable 9:16 phone preview and emits subtitle position updates", async () => {
    const wrapper = mount(SubtitlePreviewStage, {
      props: {
        activeSegment: {
          segmentIndex: 0,
          text: "字幕预览",
          startMs: 0,
          endMs: 3000,
          confidence: null,
          locked: false
        },
        status: "ready",
        styleConfig: {
          preset: "default",
          fontSize: 32,
          position: "bottom",
          textColor: "#FFFFFF",
          background: "rgba(0,0,0,0.62)",
          lineHeight: 1.35,
          boxWidth: 72,
          offsetX: 0,
          offsetY: 0
        }
      }
    });

    const frame = wrapper.get('[data-testid="subtitle-preview-frame"]');
    Object.defineProperty(frame.element, "getBoundingClientRect", {
      value: () => ({
        left: 0,
        top: 0,
        width: 300,
        height: 533,
        right: 300,
        bottom: 533,
        x: 0,
        y: 0,
        toJSON: () => ({})
      })
    });

    await wrapper.get('[data-testid="subtitle-overlay"]').trigger("pointerdown", {
      clientX: 180,
      clientY: 280,
      pointerId: 1
    });
    window.dispatchEvent(pointerLikeEvent("pointermove", { clientX: 210, clientY: 320, pointerId: 1 }));
    window.dispatchEvent(pointerLikeEvent("pointerup", { clientX: 210, clientY: 320, pointerId: 1 }));

    expect(frame.attributes("data-ratio")).toBe("9:16");
    expect(wrapper.emitted("update-style")?.at(-1)?.[0]).toMatchObject({
      offsetX: 20,
      offsetY: -18
    });
  });
});

function pointerLikeEvent(type: string, init: { clientX: number; clientY: number; pointerId: number }): PointerEvent {
  const event = new MouseEvent(type, {
    bubbles: true,
    clientX: init.clientX,
    clientY: init.clientY
  });
  Object.defineProperty(event, "pointerId", { value: init.pointerId });
  return event as PointerEvent;
}
