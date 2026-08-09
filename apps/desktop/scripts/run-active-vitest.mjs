import { spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { validateTestInventory } from "./validate-test-inventory.mjs";

const scriptPath = fileURLToPath(import.meta.url);
const desktopRoot = path.resolve(path.dirname(scriptPath), "..");
const category = readCategory(process.argv.slice(2));

try {
  const inventory = await validateTestInventory();
  const tests = inventory.vitest[category];
  if (tests.length === 0) {
    console.log(`[desktop-test] ${category} 当前没有测试。`);
    process.exit(0);
  }
  const vitestPath = path.join(
    desktopRoot,
    "node_modules",
    "vitest",
    "vitest.mjs"
  );
  const result = spawnSync(
    process.execPath,
    [vitestPath, "run", ...tests],
    {
      cwd: desktopRoot,
      encoding: "utf8",
      env: { ...process.env, TK_OPS_TEST_CATEGORY: category },
      maxBuffer: 16 * 1024 * 1024
    }
  );
  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  const combined = `${result.stdout || ""}\n${result.stderr || ""}`;
  const routerWarnings = combined.match(/\[Vue Router warn\]/gu) ?? [];
  if (routerWarnings.length > 0) {
    throw new Error(`检测到 ${routerWarnings.length} 条 Vue Router 警告。`);
  }
} catch (error) {
  console.error(
    `[desktop-test] 失败：${error instanceof Error ? error.message : "未知错误"}`
  );
  process.exitCode = 1;
}

function readCategory(args) {
  const index = args.indexOf("--category");
  const value = index >= 0 ? args[index + 1] : "active";
  if (!new Set(["active", "compatibility"]).has(value)) {
    throw new Error("测试分类只允许 active 或 compatibility。");
  }
  return value;
}
