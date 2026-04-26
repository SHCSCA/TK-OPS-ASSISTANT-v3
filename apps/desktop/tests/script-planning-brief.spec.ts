import { describe, expect, it } from "vitest";

import { buildScriptPlanningPrompt, createDefaultPlanningBrief } from "@/pages/scripts/script-planning-brief";

describe("script planning brief", () => {
  it("builds a structured script prompt from planning fields", () => {
    const brief = createDefaultPlanningBrief();
    brief.videoTheme = "春日咖啡冷饮";
    brief.productService = "冰霸杯";
    brief.targetUsers = "办公室人群";
    brief.videoGoal = "种草";
    brief.duration = "30秒";
    brief.accountPositioning = "种草号";
    brief.videoStyle = "真实口播";
    brief.shootingConditions = "产品实拍";
    brief.languageRequirement = "中文";
    brief.forbiddenContent = "不要夸大承诺";

    const prompt = buildScriptPlanningPrompt(brief);

    expect(prompt).toContain("视频主题：春日咖啡冷饮");
    expect(prompt).toContain("产品/服务：冰霸杯");
    expect(prompt).toContain("目标用户：办公室人群");
    expect(prompt).toContain("视频目的：种草");
    expect(prompt).toContain("视频时长：30秒");
    expect(prompt).toContain("账号定位：种草号");
    expect(prompt).toContain("视频风格：真实口播");
    expect(prompt).toContain("拍摄条件：产品实拍");
    expect(prompt).toContain("语言要求：中文");
    expect(prompt).toContain("禁止内容：不要夸大承诺");
    expect(prompt).toContain("请输出 Markdown 格式脚本");
  });
});
