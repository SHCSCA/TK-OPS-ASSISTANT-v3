import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const repoRoot = process.cwd();

const rootPackagePath = path.join(repoRoot, "package.json");
const cargoPath = path.join(repoRoot, "apps", "desktop", "src-tauri", "Cargo.toml");
const cargoLockPath = path.join(repoRoot, "apps", "desktop", "src-tauri", "Cargo.lock");
const pyprojectPath = path.join(repoRoot, "apps", "py-runtime", "pyproject.toml");
const runtimeVersionPath = path.join(
  repoRoot,
  "apps",
  "py-runtime",
  "src",
  "app",
  "version.py"
);
const tauriConfigPath = path.join(repoRoot, "apps", "desktop", "src-tauri", "tauri.conf.json");

async function readText(filePath) {
  return fs.readFile(filePath, "utf8");
}

async function writeTextIfChanged(filePath, nextContent) {
  const currentContent = await readText(filePath);
  if (currentContent === nextContent) {
    return false;
  }
  await fs.writeFile(filePath, nextContent, "utf8");
  return true;
}

function resolveRootVersion(packageJsonText) {
  const packageJson = JSON.parse(packageJsonText);
  if (typeof packageJson.version !== "string" || packageJson.version.trim() === "") {
    throw new Error("根 package.json 缺少有效的 version 字段。");
  }
  return packageJson.version.trim();
}

function syncCargoVersion(content, version) {
  const versionPattern = /^version\s*=\s*"[^"]*"/m;
  if (!versionPattern.test(content)) {
    throw new Error("Cargo.toml 中未找到 package version 字段。");
  }
  return content.replace(versionPattern, `version = "${version}"`);
}

function syncCargoLockVersion(content, version) {
  const packagePattern = /(\[\[package\]\]\r?\nname = "tk-ops-desktop"\r?\nversion = ")[^"]+(")/;
  if (!packagePattern.test(content)) {
    throw new Error("Cargo.lock 中未找到 tk-ops-desktop package version。");
  }
  return content.replace(packagePattern, `$1${version}$2`);
}

function syncPyprojectVersion(content, version) {
  const versionPattern = /(\[project\][\s\S]*?^version\s*=\s*")([^"]*)(")/m;
  if (!versionPattern.test(content)) {
    throw new Error("pyproject.toml 的 [project] 区块未找到 version 字段。");
  }
  return content.replace(versionPattern, `$1${version}$3`);
}

function syncRuntimeVersion(content, version) {
  const versionPattern = /^RUNTIME_VERSION\s*=\s*"[^"]*"/m;
  if (!versionPattern.test(content)) {
    throw new Error("app/version.py 中未找到 RUNTIME_VERSION。");
  }
  return content.replace(versionPattern, `RUNTIME_VERSION = "${version}"`);
}

function syncTauriVersion(content, version) {
  const parsed = JSON.parse(content);
  if (typeof parsed.version !== "string") {
    throw new Error("tauri.conf.json 缺少顶层 version 字段。");
  }
  parsed.version = version;
  return `${JSON.stringify(parsed, null, 2)}\n`;
}

async function main() {
  const rootVersion = resolveRootVersion(await readText(rootPackagePath));
  const changedFiles = [];

  const cargoNext = syncCargoVersion(await readText(cargoPath), rootVersion);
  if (await writeTextIfChanged(cargoPath, cargoNext)) {
    changedFiles.push(path.relative(repoRoot, cargoPath));
  }

  const cargoLockNext = syncCargoLockVersion(
    await readText(cargoLockPath),
    rootVersion
  );
  if (await writeTextIfChanged(cargoLockPath, cargoLockNext)) {
    changedFiles.push(path.relative(repoRoot, cargoLockPath));
  }

  const pyprojectNext = syncPyprojectVersion(await readText(pyprojectPath), rootVersion);
  if (await writeTextIfChanged(pyprojectPath, pyprojectNext)) {
    changedFiles.push(path.relative(repoRoot, pyprojectPath));
  }

  const runtimeVersionNext = syncRuntimeVersion(
    await readText(runtimeVersionPath),
    rootVersion
  );
  if (await writeTextIfChanged(runtimeVersionPath, runtimeVersionNext)) {
    changedFiles.push(path.relative(repoRoot, runtimeVersionPath));
  }

  const tauriNext = syncTauriVersion(await readText(tauriConfigPath), rootVersion);
  if (await writeTextIfChanged(tauriConfigPath, tauriNext)) {
    changedFiles.push(path.relative(repoRoot, tauriConfigPath));
  }

  if (changedFiles.length === 0) {
    console.log(`version-sync: 所有镜像文件已与 ${rootVersion} 一致。`);
    return;
  }

  console.log(`version-sync: 已同步到 ${rootVersion}`);
  for (const file of changedFiles) {
    console.log(`- ${file}`);
  }
}

main().catch((error) => {
  console.error(`version-sync: 失败 - ${error.message}`);
  process.exit(1);
});
