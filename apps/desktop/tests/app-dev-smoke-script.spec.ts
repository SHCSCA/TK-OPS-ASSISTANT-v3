import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("app:dev smoke 启动脚本", () => {
  it("Smoke 模式必须等待 Tauri dev 输出桌面进程启动信号", () => {
    const script = readFileSync(resolve(process.cwd(), "..", "..", "scripts", "run-desktop-app.mjs"), "utf8");

    expect(script).toContain("function waitForTauriDevReady");
    expect(script).toContain("attachTauriOutputWatchers");
    expect(script).toContain("tauriReadyPatterns");
    expect(script).toContain("stripAnsiCodes");
    expect(script).toContain("Tauri 桌面进程已启动");
    expect(script).not.toContain("Smoke 模式已确认 Runtime 与桌面前端都已就绪");
  });
});
