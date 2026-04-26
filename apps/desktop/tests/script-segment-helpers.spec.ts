import { describe, expect, it } from "vitest";

import { parseScriptSegments } from "@/pages/scripts/script-segment-helpers";

describe("script segment helpers", () => {
  it("ignores fenced markdown wrappers and separator lines", () => {
    const segments = parseScriptSegments([
      "```markdown",
      "### 春日种草冰霸杯 TIKTOK短视频脚本",
      "",
      "**视频时长**：15-25秒",
      "",
      "---",
      "",
      "### 脚本方案1：春日咖啡冷饮场景",
      "",
      "开场先给到真实工位节奏。",
      "```"
    ].join("\n"));

    expect(segments).toHaveLength(2);
    expect(segments[0]?.title).toBe("春日种草冰霸杯 TIKTOK短视频脚本");
    expect(segments[0]?.body).toContain("15-25秒");
    expect(segments[1]?.title).toBe("脚本方案1：春日咖啡冷饮场景");
  });
});
