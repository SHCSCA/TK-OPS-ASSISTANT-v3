import { describe, expect, it } from "vitest";

import { renderScriptMarkdownPreview } from "@/pages/scripts/script-markdown-preview";

describe("script markdown preview", () => {
  it("renders compact markdown tables as html table preview", () => {
    const html = renderScriptMarkdownPreview([
      "| 时间点 | 画面内容 | 台词（简洁高效） | 音效/特效 |",
      "|-------|----------|----------------|----------|",
      "| 0-2s | 主角背着运动包走进健身房/教室，手里拿着冰霸杯 | 春天了，水杯也要换成“巨无霸”。 | 轻快电子音乐+脚步声 |",
      "| 3-5s | 特写：杯身印有刻度（显示1L），里面是柠檬水/电解质水 | 一升容量，运动补水一次到位。 | 水流动态+刻度高亮 |"
    ].join("\n"));

    expect(html).toContain("<table>");
    expect(html).toContain("<th>时间点</th>");
    expect(html).toContain("<td>主角背着运动包走进健身房/教室，手里拿着冰霸杯</td>");
  });

  it("strips the outer markdown fence before rendering", () => {
    const html = renderScriptMarkdownPreview(["```markdown", "# 标题", "", "正文", "```"].join("\n"));

    expect(html).toContain("<h1>标题</h1>");
    expect(html).not.toContain("```");
    expect(html).not.toContain("markdown");
  });
});
