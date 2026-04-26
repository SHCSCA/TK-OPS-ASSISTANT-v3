import { describe, expect, it } from "vitest";

import {
  buildScriptDocumentViewModel,
  extractScriptDocumentDownstreamText
} from "@/modules/scripts/script-document-view-model";

describe("script document json view model", () => {
  it("renders structured script json as table-like sections without markdown parsing", () => {
    const view = buildScriptDocumentViewModel({
      schemaVersion: "script_document_v1",
      title: "春日咖啡冷饮短视频脚本",
      metadata: {
        platform: "TikTok",
        videoRatio: "9:16",
        duration: "30秒",
        targetUsers: "办公室人群"
      },
      segments: [
        {
          segmentId: "S01",
          time: "0-3秒",
          goal: "钩子",
          voiceover: "下午三点别再喝温咖啡了。",
          subtitle: "下午三点，拒绝温咖啡",
          visualSuggestion: "手把旧杯推开",
          retentionPoint: "痛点直击",
          storyboardHint: "桌面特写"
        }
      ],
      voiceoverFull: "下午三点别再喝温咖啡了。",
      subtitles: ["下午三点，拒绝温咖啡"],
      cta: {
        comment: "你下午喝冰咖啡吗？"
      }
    });

    expect(view.title).toBe("春日咖啡冷饮短视频脚本");
    expect(view.infoTable.rows).toContainEqual(["平台", "TikTok"]);
    expect(view.segmentTable.headers).toEqual([
      "段落ID",
      "时间",
      "段落目标",
      "口播文案",
      "屏幕字幕",
      "基础画面建议",
      "留存点",
      "给分镜Agent的提示"
    ]);
    expect(view.segmentTable.rows[0][3]).toBe("下午三点别再喝温咖啡了。");
    expect(view.sections.some((section) => section.title === "结尾 CTA")).toBe(true);
  });

  it("extracts voice and subtitle text from structured json before legacy markdown", () => {
    const documentJson = {
      schemaVersion: "script_document_v1",
      segments: [
        {
          segmentId: "S01",
          voiceover: "第一句口播",
          subtitle: "第一句字幕"
        },
        {
          segmentId: "S02",
          voiceover: "第二句口播",
          subtitle: "第二句字幕"
        }
      ],
      voiceoverFull: "完整口播一\n完整口播二",
      subtitles: ["字幕一", "字幕二"]
    };

    expect(extractScriptDocumentDownstreamText(documentJson, "voice").map((item) => item.text)).toEqual([
      "完整口播一",
      "完整口播二"
    ]);
    expect(extractScriptDocumentDownstreamText(documentJson, "subtitle").map((item) => item.text)).toEqual([
      "字幕一",
      "字幕二"
    ]);
  });
});
