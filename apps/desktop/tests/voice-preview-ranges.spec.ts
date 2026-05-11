import { describe, expect, it } from "vitest";

import { buildVoicePreviewRanges, formatPreviewTime } from "@/modules/voice/voice-preview-ranges";
import type { Paragraph } from "@/stores/voice-studio";

describe("配音段落预览区间", () => {
  it("按真实音频总时长缩放段落估算区间", () => {
    const ranges = buildVoicePreviewRanges(
      [
        paragraph("第一段", 4),
        paragraph("第二段", 6),
        paragraph("第三段", 10)
      ],
      10
    );

    expect(ranges).toEqual([
      { endSec: 2, index: 0, startSec: 0 },
      { endSec: 5, index: 1, startSec: 2 },
      { endSec: 10, index: 2, startSec: 5 }
    ]);
  });

  it("音频总时长不可用时使用估算时长", () => {
    const ranges = buildVoicePreviewRanges([paragraph("第一段", 3), paragraph("第二段", 5)]);

    expect(ranges).toEqual([
      { endSec: 3, index: 0, startSec: 0 },
      { endSec: 8, index: 1, startSec: 3 }
    ]);
  });

  it("格式化预览时间为分秒", () => {
    expect(formatPreviewTime(0)).toBe("00:00");
    expect(formatPreviewTime(65.4)).toBe("01:05");
  });
});

function paragraph(text: string, estimatedDuration: number): Paragraph {
  return {
    estimatedDuration,
    speechText: text,
    text
  };
}
