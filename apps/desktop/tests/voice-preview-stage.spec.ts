import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import VoicePreviewStage from "@/modules/voice/VoicePreviewStage.vue";

describe("配音预览台", () => {
  it("缺少段落预览参数时仍保留中间预览台", () => {
    const wrapper = mount(VoicePreviewStage, {
      props: {
        activeParagraph: null,
        generationMessage: null,
        selectedProfile: null,
        selectedTrack: {
          id: "voice-1",
          projectId: "project-1",
          timelineId: null,
          source: "tts",
          provider: "volcengine_tts",
          voiceName: "小何 2.0",
          filePath: "G:/runtime/voice/voice-1.mp3",
          segments: [],
          status: "processing",
          createdAt: "2026-05-11T10:00:00Z",
          updatedAt: "2026-05-11T10:00:00Z"
        },
        stateMessage: "生成中",
        status: "generating"
      } as any
    });

    expect(wrapper.get('[data-testid="voice-preview-stage"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("配音导演台");
    expect(wrapper.text()).toContain("整段预览");
  });
});
