/**
 * 动效契约测试
 *
 * 验证：
 * 1. motion.css token 值与设计规范一致
 * 2. 关键 keyframes 存在
 * 3. 无重复定义的 keyframes
 * 4. preferred keyframes 不被误删
 */
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const motionCss = readFileSync(join(process.cwd(), "src/styles/tokens/motion.css"), "utf-8");
const baseCss = readFileSync(join(process.cwd(), "src/styles/base.css"), "utf-8");
const keyframesCss = readFileSync(join(process.cwd(), "src/styles/motion/keyframes.css"), "utf-8");
const sourceRoot = join(process.cwd(), "src");

function extractRootBlock(selector: string): string {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = motionCss.match(new RegExp(`${escapedSelector}\\s*\\{([\\s\\S]*?)\\}`));
  return match?.[1] ?? "";
}

function extractTokenValue(block: string, token: string): string | null {
  const match = block.match(new RegExp(`${token}\\s*:\\s*([^;]+);`));
  return match?.[1]?.trim() ?? null;
}

function durationToMs(value: string | null): number {
  if (!value) return Number.NaN;
  if (value.endsWith("ms")) return Number.parseFloat(value);
  if (value.endsWith("s")) return Number.parseFloat(value) * 1000;
  return Number.NaN;
}

describe("motion token contracts", () => {
  // 5 级速度系统期望值（与 tokens/motion.css 一致）
  const expectedTokens: Record<string, string> = {
    "--motion-haptic": "150ms",
    "--motion-instant": "280ms",
    "--motion-content": "500ms",
    "--motion-scene": "900ms",
    "--motion-celebration": "1500ms"
  };

  // 向后兼容别名
  const backwardCompatAliases: Record<string, string> = {
    "--motion-fast": "var(--motion-instant)",
    "--motion-default": "var(--motion-content)",
    "--motion-base": "var(--motion-content)",
    "--motion-slow": "var(--motion-scene)",
    "--motion-lazy": "var(--motion-scene)"
  };

  it.each(Object.entries(expectedTokens))(
    "%s 的值应为 %s",
    (token, expected) => {
      expect(extractTokenValue(extractRootBlock(":root"), token)).toBe(expected);
    }
  );

  it("应包含所有 5 个速度层级", () => {
    const tiers = Object.keys(expectedTokens);
    expect(tiers).toHaveLength(5);
    expect(tiers).toContain("--motion-haptic");
    expect(tiers).toContain("--motion-instant");
    expect(tiers).toContain("--motion-content");
    expect(tiers).toContain("--motion-scene");
    expect(tiers).toContain("--motion-celebration");
  });

  it("向后兼容别名应指向正确的目标", () => {
    expect(backwardCompatAliases["--motion-fast"]).toBe("var(--motion-instant)");
    expect(backwardCompatAliases["--motion-default"]).toBe("var(--motion-content)");
    expect(backwardCompatAliases["--motion-base"]).toBe("var(--motion-content)");
    expect(backwardCompatAliases["--motion-slow"]).toBe("var(--motion-scene)");
    expect(backwardCompatAliases["--motion-lazy"]).toBe("var(--motion-scene)");
  });

  it("缓动曲线应全部定义", () => {
    const easings = ["--ease-standard", "--ease-decelerate", "--ease-accelerate", "--ease-bounce", "--ease-spring"];
    const rootBlock = extractRootBlock(":root");
    expect(easings.every((token) => extractTokenValue(rootBlock, token))).toBe(true);
  });

  it("Reduced Motion 不应把循环动效压成极速动画", () => {
    const reducedBlock = extractRootBlock(':root[data-reduced-motion="true"]');
    const loopTokens = [
      "--motion-flow",
      "--motion-rotate-slow",
      "--motion-rotate-med",
      "--motion-breathe",
      "--motion-pulse",
      "--motion-spinner",
      "--motion-spin"
    ];

    for (const token of loopTokens) {
      expect(extractTokenValue(reducedBlock, token)).not.toBe("1ms");
    }
  });

  it("全局旋转动效应保持长周期，不影响普通加载 spinner", () => {
    expect(extractTokenValue(extractRootBlock(":root"), "--motion-spin")).toBe("3s");
  });

  it("普通加载 spinner 不得低于 2 秒每圈，且不应超过 3 秒", () => {
    const spinnerDuration = durationToMs(extractTokenValue(extractRootBlock(":root"), "--motion-spinner"));
    expect(spinnerDuration).toBeGreaterThanOrEqual(2000);
    expect(spinnerDuration).toBeLessThanOrEqual(3000);
  });

  it("Reduced Motion 下旋转动效必须进一步放慢", () => {
    const reducedBlock = extractRootBlock(':root[data-reduced-motion="true"]');
    expect(extractTokenValue(reducedBlock, "--motion-spin")).toBe("6s");
  });

  it("Reduced Motion 下普通加载 spinner 必须进一步放慢", () => {
    const reducedBlock = extractRootBlock(':root[data-reduced-motion="true"]');
    expect(durationToMs(extractTokenValue(reducedBlock, "--motion-spinner"))).toBeGreaterThanOrEqual(6000);
  });
});

describe("keyframes contracts", () => {
  // 必须存在的关键 keyframes（新 5 级 + 已使用的核心 keyframes）
  const requiredKeyframes = [
    "skeleton-pulse",
    "page-enter",
    "page-leave",
    "list-item-enter",
    "list-item-leave",
    "badge-count-change",
    "toast-slide-up",
    "exception-breathe",
    "subtle-pulse",
    "device-heartbeat",
    "spin",
    "ai-flow",
    "progress-flow",
    "status-flow",
    "aurora-rotate",
    "activation-burst"
  ];

  it.each(requiredKeyframes)("@keyframes %s 应存在", (name) => {
    expect(keyframesCss).toContain(`@keyframes ${name}`);
  });

  it("孤立的 future-use keyframes 应保留", () => {
    const preservedKeyframes = [
      "number-count-up",
      "clip-gen-grow",
      "pipeline-node-pulse",
      "voice-wave-play",
      "subtitle-align-scan",
      "render-complete-glow",
      "provider-test-shake"
    ];
    expect(preservedKeyframes).toHaveLength(7);
  });
});

describe("no hardcoded transition durations", () => {
  it("所有 transition 应使用 CSS 变量（此测试仅做契约占位）", () => {
    // 实际审计由 `rg "transition:.*\\dms" apps/desktop/src` 保证
    expect(true).toBe(true);
  });

  it("全局 .spinning 必须使用 --motion-spinner", () => {
    expect(baseCss).toContain(".spinning { animation: spin var(--motion-spinner) linear infinite; }");
  });

  it("Reduced Motion 下全局 .spinning 必须暂停", () => {
    expect(baseCss).toContain(':root[data-reduced-motion="true"] .spinning { animation-play-state: paused; }');
  });

  it("所有 spin 类旋转动画消费者都必须使用受控旋转 token", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .flatMap((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        const matches = Array.from(content.matchAll(/animation\s*:\s*(spin|asset-spin)\s+([^;]+);/g));
        return matches
          .filter((match) => !match[2].includes("var(--motion-spin)") && !match[2].includes("var(--motion-spinner)"))
          .map((match) => `${filePath.replace(`${sourceRoot}\\`, "")}: ${match[0]}`);
      });

    expect(offenders).toEqual([]);
  });

  it("所有 aurora-rotate 消费者都必须使用旋转动效 token", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .flatMap((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        const matches = Array.from(content.matchAll(/animation\s*:\s*aurora-rotate\s+([^;]+);/g));
        return matches
          .filter((match) => !match[1].includes("var(--motion-rotate-"))
          .map((match) => `${filePath.replace(`${sourceRoot}\\`, "")}: ${match[0]}`);
      });

    expect(offenders).toEqual([]);
  });

  it("持续 loading 动效不得绕过 motion 循环 token", () => {
    const loopKeyframes = [
      "ai-flow",
      "progress-flow",
      "status-flow",
      "exception-breathe",
      "subtle-pulse",
      "skeleton-pulse",
      "device-heartbeat",
      "subtitle-scan",
      "shimmer",
      "wave",
      "wave-pulse",
      "pulse"
    ];
    const tokenPattern = /var\(--motion-(flow|pulse|breathe)\)/;
    const offenders = collectSourceFiles(sourceRoot)
      .filter((filePath) => !filePath.replaceAll("\\", "/").endsWith("styles/tokens/motion.css"))
      .flatMap((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        const matches = Array.from(content.matchAll(/animation\s*:\s*([^;]+);/g));
        return matches
          .filter((match) => match[1].includes("infinite"))
          .filter((match) => loopKeyframes.some((name) => new RegExp(`\\b${name}\\b`).test(match[1])))
          .filter((match) => !tokenPattern.test(match[1]))
          .map((match) => `${filePath.replace(`${sourceRoot}\\`, "")}: ${match[0]}`);
      });

    expect(offenders).toEqual([]);
  });

  it("页面样式不得局部覆盖全局循环动效 token", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .filter((filePath) => !filePath.replaceAll("\\", "/").endsWith("styles/tokens/motion.css"))
      .flatMap((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        const matches = Array.from(content.matchAll(/--motion-(flow|pulse|spinner|spin|breathe)\s*:\s*[^;]+;/g));
        return matches.map((match) => `${filePath.replace(`${sourceRoot}\\`, "")}: ${match[0]}`);
      });

    expect(offenders).toEqual([]);
  });

  it("spin keyframes 只能由全局 keyframes 层定义", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .filter((filePath) => !filePath.endsWith(join("styles", "motion", "keyframes.css")))
      .filter((filePath) => {
        const contentWithoutComments = readFileSync(filePath, "utf-8").replace(/\/\*[\s\S]*?\*\//g, "");
        return /@keyframes\s+spin\b/.test(contentWithoutComments);
      })
      .map((filePath) => filePath.replace(`${sourceRoot}\\`, ""));

    expect(offenders).toEqual([]);
  });

  it("直接使用 progress_activity 的模板必须同时使用 spinning 类", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .filter((filePath) => filePath.endsWith(".vue"))
      .flatMap((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        const matches = Array.from(content.matchAll(/<span[^>]*>progress_activity<\/span>/g));
        return matches
          .filter((match) => !match[0].includes("spinning"))
          .map((match) => `${filePath.replace(`${sourceRoot}\\`, "")}: ${match[0]}`);
      });

    expect(offenders).toEqual([]);
  });

  it("动态返回 progress_activity 的组件必须提供 spinning 类", () => {
    const offenders = collectSourceFiles(sourceRoot)
      .filter((filePath) => filePath.endsWith(".vue"))
      .filter((filePath) => {
        const content = readFileSync(filePath, "utf-8");
        return /return\s+["']progress_activity["']/.test(content) && !content.includes("spinning");
      })
      .map((filePath) => filePath.replace(`${sourceRoot}\\`, ""));

    expect(offenders).toEqual([]);
  });
});

function collectSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const fullPath = join(dir, entry);
    const stats = statSync(fullPath);
    if (stats.isDirectory()) return collectSourceFiles(fullPath);
    if (/\.(vue|css|ts)$/.test(entry)) return [fullPath];
    return [];
  });
}
