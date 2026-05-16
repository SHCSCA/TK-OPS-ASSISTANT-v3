import { describe, expect, it } from "vitest";

import {
  buildStoryboardScenesFromJson,
  buildStoryboardViewModel
} from "@/modules/storyboards/storyboard-document-view-model";

describe("storyboard document json view model", () => {
  it("uses storyboard json shots as the single source for the list workspace", () => {
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

  it("does not surface continuation placeholders in voiceover and subtitle cells", () => {
    const storyboardJson = {
      schemaVersion: "storyboard_document_v1",
      shots: [
        {
          shotId: "SH01",
          segmentId: "S01",
          time: "0-3秒",
          voiceover: "This lamp made me cancel my dinner plan.",
          subtitle: "This lamp made me cancel my dinner plan.",
          visualContent: "墙灯打开，房间亮起"
        },
        {
          shotId: "SH02",
          segmentId: "S01",
          time: "3-5秒",
          voiceover: "（延续上句口播）",
          subtitle: "(延续上句字幕)",
          visualContent: "手机关闭订单页"
        },
        {
          shotId: "SH03",
          segmentId: "S02",
          time: "5-8秒",
          voiceover: "(延续口播)",
          subtitle: "（延续字幕）",
          visualContent: "房间暖光亮起"
        }
      ]
    };

    const view = buildStoryboardViewModel(storyboardJson);
    const secondRow = view.shotTable.rows[1];
    const thirdRow = view.shotTable.rows[2];

    expect(secondRow.join(" ")).not.toContain("延续上句");
    expect(secondRow[8]).toBe("");
    expect(secondRow[9]).toBe("");
    expect(thirdRow.join(" ")).not.toContain("延续");
    expect(thirdRow[8]).toBe("");
    expect(thirdRow[9]).toBe("");
  });
});
