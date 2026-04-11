import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const repoRoot = process.cwd();

const rootPackagePath = path.join(repoRoot, "package.json");
const desktopPackagePath = path.join(repoRoot, "apps", "desktop", "package.json");
const cargoPath = path.join(repoRoot, "apps", "desktop", "src-tauri", "Cargo.toml");
const pyprojectPath = path.join(repoRoot, "apps", "py-runtime", "pyproject.toml");
const tauriConfigPath = path.join(repoRoot, "apps", "desktop", "src-tauri", "tauri.conf.json");
const docsRoot = path.join(repoRoot, "docs");
const readmePath = path.join(repoRoot, "README.md");

async function readText(filePath) {
  return fs.readFile(filePath, "utf8");
}

function getRootVersion(packageJsonText) {
  const pkg = JSON.parse(packageJsonText);
  if (typeof pkg.version !== "string" || pkg.version.trim() === "") {
    throw new Error("根 package.json 缺少有效 version。");
  }
  return pkg.version.trim();
}

function getCargoVersion(content) {
  const match = content.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) {
    throw new Error("Cargo.toml 未找到 package version。");
  }
  return match[1];
}

function getPyprojectVersion(content) {
  const match = content.match(/\[project\][\s\S]*?^version\s*=\s*"([^"]+)"/m);
  if (!match) {
    throw new Error("pyproject.toml 的 [project] 区块未找到 version。");
  }
  return match[1];
}

function getTauriVersion(content) {
  const parsed = JSON.parse(content);
  if (typeof parsed.version !== "string") {
    throw new Error("tauri.conf.json 缺少 version。");
  }
  return parsed.version;
}

async function collectMarkdownFiles(dir) {
  const result = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      result.push(...(await collectMarkdownFiles(fullPath)));
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".md")) {
      result.push(fullPath);
    }
  }
  return result;
}

function collectUsersPathLines(content) {
  const lines = content.split(/\r?\n/);
  const matches = [];
  lines.forEach((line, index) => {
    if (line.includes("/Users/")) {
      matches.push({ lineNumber: index + 1, line: line.trim() });
    }
  });
  return matches;
}

async function main() {
  const errors = [];
  const rootVersion = getRootVersion(await readText(rootPackagePath));

  const cargoVersion = getCargoVersion(await readText(cargoPath));
  if (cargoVersion !== rootVersion) {
    errors.push(`${path.relative(repoRoot, cargoPath)} 版本为 ${cargoVersion}，应为 ${rootVersion}`);
  }

  const pyprojectVersion = getPyprojectVersion(await readText(pyprojectPath));
  if (pyprojectVersion !== rootVersion) {
    errors.push(`${path.relative(repoRoot, pyprojectPath)} 版本为 ${pyprojectVersion}，应为 ${rootVersion}`);
  }

  const tauriVersion = getTauriVersion(await readText(tauriConfigPath));
  if (tauriVersion !== rootVersion) {
    errors.push(`${path.relative(repoRoot, tauriConfigPath)} 版本为 ${tauriVersion}，应为 ${rootVersion}`);
  }

  const desktopPackage = JSON.parse(await readText(desktopPackagePath));
  if (Object.hasOwn(desktopPackage, "version")) {
    errors.push(`${path.relative(repoRoot, desktopPackagePath)} 不应维护 version 字段`);
  }

  const markdownFiles = [readmePath, ...(await collectMarkdownFiles(docsRoot))];
  for (const filePath of markdownFiles) {
    const content = await readText(filePath);
    const relativeFile = path.relative(repoRoot, filePath);
    const lines = content.split(/\r?\n/);

    lines.forEach((line, index) => {
      const hasVersionWord = line.includes("版本");
      const semverMatch = line.match(/\b\d+\.\d+\.\d+\b/);
      if (hasVersionWord && semverMatch) {
        errors.push(`${relativeFile}:${index + 1} 存在硬编码版本号：${semverMatch[0]}`);
      }
    });

    const usersPathHits = collectUsersPathLines(content);
    for (const hit of usersPathHits) {
      errors.push(`${relativeFile}:${hit.lineNumber} 存在本地绝对路径 /Users/`);
    }
  }

  if (errors.length > 0) {
    console.error("version-check: 失败");
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exit(1);
  }

  console.log(`version-check: 通过（主版本 ${rootVersion}）`);
}

main().catch((error) => {
  console.error(`version-check: 失败 - ${error.message}`);
  process.exit(1);
});
