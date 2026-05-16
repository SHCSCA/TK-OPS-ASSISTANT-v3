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

  it("导演台展示当前脚本段数而不是旧音轨片段数", () => {
    const wrapper = mount(VoicePreviewStage, {
      props: {
        activeParagraph: {
          estimatedDuration: 3,
          speechText: "第一段脚本！",
          text: "第一段脚本！"
        },
        generationMessage: null,
        paragraphs: [
          { estimatedDuration: 3, speechText: "第一段脚本！", text: "第一段脚本！" },
          { estimatedDuration: 3, speechText: "第二段脚本！", text: "第二段脚本！" },
          { estimatedDuration: 3, speechText: "第三段脚本！", text: "第三段脚本！" }
        ],
        selectedProfile: voiceProfile(),
        selectedTrack: {
          ...voiceTrack(),
          segments: Array.from({ length: 5 }, (_, index) => ({
            audioAssetId: null,
            endMs: null,
            segmentIndex: index,
            startMs: null,
            text: `旧音轨 ${index + 1}`
          }))
        },
        stateMessage: "就绪",
        status: "ready"
      } as any
    });

    const text = wrapper.get('[data-testid="voice-preview-stage"]').text();
    expect(text).toContain("脚本段数");
    expect(text).toContain("3 段");
    expect(text).not.toContain("片段数量");
  });
});

function voiceProfile() {
  return {
    id: "alloy-zh",
    provider: "volcengine_tts",
    voiceId: "zh_female_vv_uranus_bigtts",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: true
  };
}

function voiceTrack() {
  return {
    createdAt: "2026-05-11T10:00:00Z",
    filePath: "G:/runtime/voice/voice-1.mp3",
    id: "voice-1",
    projectId: "project-1",
    provider: "volcengine_tts",
    segments: [],
    source: "tts",
    status: "ready",
    timelineId: null,
    updatedAt: "2026-05-11T10:00:00Z",
    voiceName: "清晰叙述"
  };
}
