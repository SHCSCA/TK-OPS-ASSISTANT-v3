import type { StoryboardScene } from "@/types/runtime";

export function buildStoryboardMarkdown(scenes: StoryboardScene[]): string {
  if (scenes.length === 0) {
    return "";
  }

  if (shouldUseLooseFallback(scenes)) {
    return buildLooseStoryboardMarkdown(scenes);
  }

  const rows = scenes.map((scene, index) =>
    [
      scene.shotLabel || `镜头${index + 1}`,
      scene.time || "",
      scene.shotSize || "",
      scene.visualContent || scene.summary || "",
      scene.action || "",
      scene.cameraAngle || "",
      scene.cameraMovement || "",
      scene.voiceover || "",
      scene.subtitle || "",
      scene.audio || "",
      scene.transition || "",
      scene.shootingNote || ""
    ]
      .map(escapeCell)
      .join(" | ")
  );

  const promptSections = scenes
    .map((scene, index) => {
      const prompt = (scene.visualPrompt ?? "").trim();
      if (!prompt) return "";
      return [
        `### 镜头${index + 1} AI画面提示词`,
        "",
        "中文提示词：",
        "",
        "```text",
        prompt,
        "```"
      ].join("\n");
    })
    .filter(Boolean);

  return [
    "# TikTok 分镜执行方案",
    "",
    "## 详细分镜表",
    "",
    "| 镜头 | 时间 | 景别 | 画面内容 | 人物动作 | 镜头角度 | 运镜方式 | 口播文案 | 屏幕字幕 | 音效/BGM | 转场方式 | 拍摄注意 |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ...rows.map((row) => `| ${row} |`),
    "",
    "## 每个镜头的画面提示词",
    "",
    ...promptSections
  ].join("\n");
}

function buildLooseStoryboardMarkdown(scenes: StoryboardScene[]): string {
  const sections = scenes.map((scene, index) => {
    const title = cleanHeading(scene.shotLabel || scene.title || `分镜 ${index + 1}`);
    const body = scene.visualContent || scene.summary || scene.visualPrompt || "待补充分镜内容。";
    const prompt = scene.visualPrompt && scene.visualPrompt !== body
      ? ["", "AI 画面提示词：", "", "```text", scene.visualPrompt, "```"].join("\n")
      : "";
    return [`## ${title}`, "", body, prompt].filter(Boolean).join("\n");
  });

  return [
    "# TikTok 分镜执行方案",
    "",
    "> 当前版本缺少 AI 原始 Markdown，以下内容由结构化分镜兜底还原。",
    "",
    ...sections
  ].join("\n\n");
}

function shouldUseLooseFallback(scenes: StoryboardScene[]): boolean {
  if (scenes.length > 40) {
    return true;
  }
  return scenes.some((scene) => {
    const title = `${scene.title ?? ""}${scene.shotLabel ?? ""}`;
    const body = `${scene.visualContent ?? ""}${scene.summary ?? ""}`;
    return title.trim().startsWith("#") || body.includes("| 项目 | 内容 |") || body.includes("|---|");
  });
}

function cleanHeading(value: string): string {
  return value.replace(/^#+\s*/, "").trim() || "未命名分镜";
}

export function sceneDisplayTitle(scene: StoryboardScene, index: number): string {
  return scene.shotLabel || scene.title || `镜头${index + 1}`;
}

export function scenePrimarySummary(scene: StoryboardScene): string {
  return scene.visualContent || scene.summary || "待补充分镜画面。";
}

export function sceneMetaLine(scene: StoryboardScene): string {
  return [scene.time, scene.shotSize, scene.cameraAngle, scene.cameraMovement]
    .filter(Boolean)
    .join(" · ");
}

function escapeCell(value: string): string {
  return value.replace(/\|/g, "／").replace(/\n/g, "<br>");
}
