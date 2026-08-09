import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const desktopRoot = path.resolve(path.dirname(scriptPath), "..");
const inventoryPath = path.join(
  desktopRoot,
  "tests",
  "test-inventory.v1.json"
);
const categories = ["active", "compatibility", "retired"];
const forbiddenActivePatterns = [
  /seedExecutionBinding/u,
  /seed-execution-binding\.py/u,
  /完整机器码[^\n]*\.fill/u,
  /\b(?:INSERT|UPDATE)\s+(?:INTO\s+)?(?:device_workspaces|browser_instances|execution_bindings)\b/iu
];

export async function validateTestInventory() {
  const inventory = JSON.parse(await readFile(inventoryPath, "utf8"));
  if (inventory.schemaVersion !== 1) {
    throw new Error("测试库存 schemaVersion 必须为 1。");
  }

  const actualVitest = await collectTests(".spec.ts");
  const actualPlaywright = await collectTests(".e2e.ts");
  validateSuite("vitest", inventory.vitest, actualVitest);
  validateSuite("playwright", inventory.playwright, actualPlaywright);
  await validateActiveSources([
    ...inventory.vitest.active,
    ...inventory.playwright.active
  ]);

  return inventory;
}

async function collectTests(suffix) {
  const testsRoot = path.join(desktopRoot, "tests");
  const files = [];
  await walk(testsRoot, files);
  return files
    .filter((file) => file.endsWith(suffix))
    .map((file) => normalize(path.relative(desktopRoot, file)))
    .sort();
}

async function walk(directory, files) {
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await walk(target, files);
    } else if (entry.isFile()) {
      files.push(target);
    }
  }
}

function validateSuite(name, suite, actual) {
  if (!suite || typeof suite !== "object") {
    throw new Error(`${name} 测试库存缺失。`);
  }
  const declared = [];
  for (const category of categories) {
    const entries = suite[category];
    if (!Array.isArray(entries)) {
      throw new Error(`${name}.${category} 必须是数组。`);
    }
    for (const entry of entries) {
      if (typeof entry !== "string" || !entry.startsWith("tests/")) {
        throw new Error(`${name}.${category} 包含非法路径。`);
      }
      declared.push(normalize(entry));
    }
  }
  const duplicates = declared.filter(
    (entry, index) => declared.indexOf(entry) !== index
  );
  if (duplicates.length > 0) {
    throw new Error(`${name} 测试重复分类：${[...new Set(duplicates)].join(", ")}`);
  }
  const missing = actual.filter((entry) => !declared.includes(entry));
  const stale = declared.filter((entry) => !actual.includes(entry));
  if (missing.length > 0 || stale.length > 0) {
    throw new Error(
      `${name} 库存不一致；未登记=${missing.join(", ") || "无"}；`
      + `失效=${stale.join(", ") || "无"}`
    );
  }
}

async function validateActiveSources(entries) {
  for (const entry of entries) {
    const source = await readFile(path.join(desktopRoot, entry), "utf8");
    const forbidden = forbiddenActivePatterns.find((pattern) => pattern.test(source));
    if (forbidden) {
      throw new Error(`active 测试包含生产绕过：${entry} (${forbidden})`);
    }
  }
}

function normalize(value) {
  return value.replaceAll("\\", "/");
}

async function main() {
  const inventory = await validateTestInventory();
  console.log(
    `[test-inventory] 通过：Vitest active=${inventory.vitest.active.length} `
    + `compatibility=${inventory.vitest.compatibility.length} `
    + `retired=${inventory.vitest.retired.length}；Playwright active=`
    + `${inventory.playwright.active.length} compatibility=`
    + `${inventory.playwright.compatibility.length} `
    + `retired=${inventory.playwright.retired.length}`
  );
}

if (path.resolve(process.argv[1] || "") === scriptPath) {
  main().catch((error) => {
    console.error(
      `[test-inventory] 失败：${error instanceof Error ? error.message : "未知错误"}`
    );
    process.exitCode = 1;
  });
}
