import type {
  VideoContentStructureDto,
  VideoDeconstructionResultDto,
  VideoScriptLineDto
} from "@/types/runtime";

export type VideoResultTabId = "script" | "keyframes" | "structure";

export type VideoScriptDisplayLine = {
  key: string;
  timeLabel: string;
  primary: string;
  secondary: string;
  type: string;
};

export type VideoStructureDisplayTag = {
  id: string;
  label: string;
  tone: "hook" | "scene" | "value" | "proof" | "cta" | "risk";
};

export type VideoStructureDisplayBlock = {
  id: string;
  title: string;
  body: string;
  evidence: string[];
  tone: "hook" | "scene" | "value" | "proof" | "cta" | "risk";
};

export function buildScriptDisplayLines(
  result: VideoDeconstructionResultDto | null,
  fallbackText: string
): VideoScriptDisplayLine[] {
  const standardLines = result?.script?.lines ?? [];
  if (standardLines.length > 0) {
    return standardLines.map(scriptLineToDisplayLine).filter((line) => line.primary || line.secondary);
  }
  return fallbackText
    .split(/\r?\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const parts = splitDisplayLineText(line);
      return {
        key: `fallback-${index}`,
        timeLabel: "未标注时间",
        primary: parts.primary,
        secondary: parts.secondary,
        type: "speech"
      };
    });
}

export function buildStructureTags(
  structure: VideoContentStructureDto | null | undefined
): VideoStructureDisplayTag[] {
  if (!structure) return [];
  const tags: VideoStructureDisplayTag[] = [];
  if (structure.hook) tags.push({ id: "hook", label: "开场钩子", tone: "hook" });
  if (structure.painPoints.length) tags.push({ id: "pain", label: "痛点触发", tone: "risk" });
  if (structure.sellingPoints.length) tags.push({ id: "scene", label: "产品/场景演示", tone: "scene" });
  if (structure.sellingPoints.length) tags.push({ id: "value", label: "产品介绍与卖点", tone: "value" });
  if (structure.rhythm.length) tags.push({ id: "rhythm", label: "使用细节与效果说明", tone: "proof" });
  if (structure.reusableForScript.length || structure.reusableForStoryboard.length) {
    tags.push({ id: "proof", label: "效果验证/证明", tone: "proof" });
  }
  if (structure.cta) tags.push({ id: "cta", label: "行动号召（CTA）", tone: "cta" });
  return tags;
}

export function buildStandardStructureBlocks(
  structure: VideoContentStructureDto | null | undefined
): VideoStructureDisplayBlock[] {
  if (!structure || !hasContentStructurePayload(structure)) return [];
  const blocks: VideoStructureDisplayBlock[] = [];
  const topicBody = joinText([structure.topic, structure.hook], "｜");
  if (topicBody) {
    blocks.push({
      id: "topic-hook",
      title: "主题与钩子",
      body: topicBody,
      evidence: buildEvidence([
        structure.hook ? `开头用“${structure.hook}”建立注意力。` : "",
        structure.topic ? `主题聚焦：${structure.topic}` : ""
      ]),
      tone: "hook"
    });
  }

  const valueBody = joinText([...structure.painPoints, ...structure.sellingPoints], "；");
  if (valueBody) {
    blocks.push({
      id: "pain-value",
      title: "痛点与卖点",
      body: valueBody,
      evidence: buildEvidence([
        structure.painPoints.length ? `先放大需求：${structure.painPoints.join("；")}` : "",
        structure.sellingPoints.length ? `再给出卖点：${structure.sellingPoints.join("；")}` : ""
      ]),
      tone: "value"
    });
  }

  const rhythmBody = joinText([...structure.rhythm, structure.cta], "；");
  if (rhythmBody) {
    blocks.push({
      id: "rhythm-cta",
      title: "节奏与 CTA",
      body: rhythmBody,
      evidence: buildEvidence([
        structure.rhythm.length ? `节奏拆解：${structure.rhythm.join("；")}` : "",
        structure.cta ? `结尾动作：${structure.cta}` : ""
      ]),
      tone: "cta"
    });
  }

  const reusableBody = joinText([...structure.reusableForScript, ...structure.reusableForStoryboard], "；");
  if (reusableBody) {
    blocks.push({
      id: "reusable",
      title: "可复用信息",
      body: reusableBody,
      evidence: buildEvidence([
        structure.reusableForScript.length ? `可复用话术：${structure.reusableForScript.join("；")}` : "",
        structure.reusableForStoryboard.length ? `可复用镜头：${structure.reusableForStoryboard.join("；")}` : ""
      ]),
      tone: "proof"
    });
  }

  if (structure.risks.length) {
    blocks.push({
      id: "risks",
      title: "风险提示",
      body: structure.risks.join("；"),
      evidence: ["发布前需要复核这些表述，避免违规或夸大。"],
      tone: "risk"
    });
  }
  return blocks;
}

export function hasContentStructurePayload(structure: VideoContentStructureDto | null | undefined): boolean {
  if (!structure) return false;
  return Boolean(
    structure.topic ||
    structure.hook ||
    structure.cta ||
    structure.painPoints.length ||
    structure.sellingPoints.length ||
    structure.rhythm.length ||
    structure.reusableForScript.length ||
    structure.reusableForStoryboard.length ||
    structure.risks.length
  );
}

export function serializeStructureBlocks(blocks: VideoStructureDisplayBlock[]): string {
  return blocks
    .map((block) => {
      const evidence = block.evidence.length ? `\n结构作用：${block.evidence.join("；")}` : "";
      return `${block.title}\n${block.body}${evidence}`;
    })
    .join("\n\n");
}

function scriptLineToDisplayLine(line: VideoScriptLineDto, index: number): VideoScriptDisplayLine {
  const parts = splitDisplayLineText(line.text.trim());
  return {
    key: `${line.startMs}-${line.endMs}-${index}`,
    timeLabel: formatRange(line.startMs, line.endMs),
    primary: parts.primary,
    secondary: parts.secondary,
    type: line.type || "speech"
  };
}

function splitDisplayLineText(text: string): { primary: string; secondary: string } {
  const slashParts = text.split(/\s+\/\s+/);
  if (slashParts.length >= 2) {
    return {
      primary: slashParts[0]?.trim() ?? "",
      secondary: slashParts.slice(1).join(" / ").trim()
    };
  }
  return { primary: text, secondary: "" };
}

function buildEvidence(items: string[]): string[] {
  return items.map((item) => item.trim()).filter(Boolean);
}

function joinText(items: Array<string | null | undefined>, separator: string): string {
  return items.map((item) => item?.trim()).filter(Boolean).join(separator);
}

function formatRange(startMs: number, endMs: number): string {
  return `${formatMs(startMs)}-${formatMs(endMs)}`;
}

function formatMs(value: number): string {
  const seconds = Math.floor(value / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = String(seconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}
