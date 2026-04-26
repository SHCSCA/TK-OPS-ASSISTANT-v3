import { describe, expect, it } from "vitest";

import {
  buildStoryboardScenesFromJson,
  buildStoryboardViewModel
} from "@/modules/storyboards/storyboard-document-view-model";

describe("storyboard document json view model", () => {
  it("uses storyboard json shots as the single source for list and preview views", () => {
    const storyboardJson = {
      schemaVersion: "storyboard_document_v1",
      metadata: {
        storyboardId: "sb-001",
        videoRatio: "9:16",
        targetDurationSec: 30
      },
      shots: [
        {
          shotId: "SH01",
          segmentId: "S01",
          time: "0-3秒",
          shotSize: "特写",
          visualContent: "手把旧杯推开，冰霸杯放到桌面中心",
          action: "人物拿起杯子",
          cameraAngle: "桌面平视",
          cameraMovement: "轻微推进",
          voiceover: "下午三点别再喝温咖啡了。 / 下午三点别再喝温咖啡了。",
          subtitle: "下午三点，拒绝温咖啡",
          audio: "冰块声",
          shootingNote: "杯身正对镜头",
          transition: "硬切",
          visualPrompt: "9:16 手机竖屏，办公室桌面"
        }
      ]
    };

    const view = buildStoryboardViewModel(storyboardJson);
    const scenes = buildStoryboardScenesFromJson(storyboardJson);

    expect(view.title).toBe("TikTok 分镜规划文档");
    expect(view.shotTable.rows[0]).toContain("SH01");
    expect(view.shotTable.rows[0]).toContain("下午三点别再喝温咖啡了。");
    expect(view.shotTable.rows[0].join(" ")).not.toContain(" / 下午三点别再喝温咖啡了。");
    expect(scenes[0]).toMatchObject({
      sceneId: "SH01",
      title: "SH01 · S01",
      voiceover: "下午三点别再喝温咖啡了。",
      subtitle: "下午三点，拒绝温咖啡"
    });
  });
});
