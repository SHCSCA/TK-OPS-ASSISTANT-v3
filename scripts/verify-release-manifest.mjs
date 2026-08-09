import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  mkdirSync,
  readFileSync,
  renameSync,
  statSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import {
  artifactBoundEvidence,
  productionArtifactKinds,
  productionTestIds
} from "./release-evidence-policy.mjs";
import { collectSourceSnapshot } from "./release-source-snapshot.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inputFiles = {
  packageLockSha256: "apps/desktop/package-lock.json",
  cargoLockSha256: "apps/desktop/src-tauri/Cargo.lock",
  pyprojectSha256: "apps/py-runtime/pyproject.toml",
  tauriConfigSha256: "apps/desktop/src-tauri/tauri.conf.json",
  runtimePublicKeySha256: "apps/py-runtime/resources/license-public.pem"
};

try {
  const options = parseArgs(process.argv.slice(2));
  const manifestPath = resolveRepoFile(options.manifest);
  const manifest = readJson(manifestPath);
  validateShape(manifest);
  validateGit(manifest);
  validateInputs(manifest);
  validateTests(manifest);
  validateArtifacts(manifest);
  validateArtifactBindings(manifest);
  if (options.promote) promote(manifest, manifestPath);
  console.log(
    `[release-manifest] 校验通过：${normalize(path.relative(repoRoot, manifestPath))} `
    + `channel=${manifest.channel} tests=${manifest.tests.length} `
    + `artifacts=${manifest.artifacts.length}`
  );
} catch (error) {
  console.error(
    `[release-manifest] 校验失败：${error instanceof Error ? error.message : "未知错误"}`
  );
  process.exitCode = 1;
}

function parseArgs(args) {
  const index = args.indexOf("--manifest");
  const manifest = index >= 0 ? args[index + 1] : "";
  if (!manifest || manifest.startsWith("--")) {
    throw new Error("必须提供 --manifest <relative/path>。");
  }
  return { manifest, promote: args.includes("--promote") };
}

function validateShape(manifest) {
  if (
    manifest.schemaVersion !== 2
    || manifest.product !== "TK-OPS"
    || !new Set(["test", "production"]).has(manifest.channel)
    || manifest.platform !== "windows"
    || manifest.architecture !== "x86_64"
    || !Array.isArray(manifest.tests)
    || !Array.isArray(manifest.artifacts)
  ) {
    throw new Error("manifest 基础结构不符合 v2 契约。");
  }
}

function validateGit(manifest) {
  const current = collectSourceSnapshot(repoRoot);
  for (const key of [
    "commit",
    "tree",
    "dirty",
    "statusSha256",
    "trackedDiffSha256",
    "untrackedContentSha256",
    "sourceSnapshotSha256"
  ]) {
    if (manifest.git?.[key] !== current[key]) {
      throw new Error(`RELEASE_SOURCE_SNAPSHOT_MISMATCH: ${key} 与当前源码不一致。`);
    }
  }
}

function validateInputs(manifest) {
  for (const [key, relativePath] of Object.entries(inputFiles)) {
    if (manifest.inputs?.[key] !== sha256File(resolveRepoFile(relativePath))) {
      throw new Error(`构建输入哈希不一致：${key}`);
    }
  }
}

function validateTests(manifest) {
  const ids = new Set();
  for (const evidence of manifest.tests) {
    if (!evidence.id || ids.has(evidence.id) || evidence.exitCode !== 0) {
      throw new Error("测试证据 ID 重复、缺失或未通过。");
    }
    ids.add(evidence.id);
    const evidencePath = resolveRepoFile(evidence.evidencePath);
    if (sha256File(evidencePath) !== evidence.evidenceSha256) {
      throw new Error(`测试证据哈希不一致：${evidence.id}`);
    }
  }
}

function validateArtifacts(manifest) {
  const kinds = new Set();
  for (const artifact of manifest.artifacts) {
    if (!artifact.kind || kinds.has(artifact.kind)) {
      throw new Error("制品 kind 缺失或重复。");
    }
    kinds.add(artifact.kind);
    const artifactPath = resolveRepoFile(artifact.path);
    const stat = statSync(artifactPath);
    if (
      !stat.isFile()
      || stat.size !== artifact.size
      || sha256File(artifactPath) !== artifact.sha256
    ) {
      throw new Error(`制品大小或哈希不一致：${artifact.kind}`);
    }
  }
}

function validateArtifactBindings(manifest) {
  const artifacts = new Map(
    manifest.artifacts.map((artifact) => [artifact.kind, artifact.sha256])
  );
  const evidenceById = new Map(
    manifest.tests.map((evidence) => [evidence.id, evidence])
  );
  for (const [evidenceId, requiredKinds] of Object.entries(artifactBoundEvidence)) {
    const evidence = evidenceById.get(evidenceId);
    if (!evidence) continue;
    for (const kind of requiredKinds) {
      const artifactSha256 = artifacts.get(kind);
      if (
        !artifactSha256
        || evidence.artifactBindings?.[kind] !== artifactSha256
      ) {
        throw new Error(`测试证据未绑定当前制品：${evidenceId}:${kind}`);
      }
    }
  }
}

function promote(manifest, manifestPath) {
  if (manifest.channel !== "production" || manifest.git.dirty) {
    throw new Error("只有干净工作树生成的 production manifest 可以提升 current。");
  }
  const artifactKinds = new Set(manifest.artifacts.map((item) => item.kind));
  const testIds = new Set(manifest.tests.map((item) => item.id));
  const missingArtifacts = productionArtifactKinds.filter((item) => !artifactKinds.has(item));
  const missingTests = productionTestIds.filter((item) => !testIds.has(item));
  if (missingArtifacts.length > 0 || missingTests.length > 0) {
    throw new Error(
      `RELEASE_REQUIRED_EVIDENCE_MISSING: 提升证据不完整；缺制品=${missingArtifacts.join(",") || "无"}；`
      + `缺测试=${missingTests.join(",") || "无"}`
    );
  }
  const pointerPath = resolveRepoFile("dist/releases/current.json");
  mkdirSync(path.dirname(pointerPath), { recursive: true });
  const pointer = {
    schemaVersion: 2,
    manifestPath: normalize(path.relative(repoRoot, manifestPath)),
    manifestSha256: sha256File(manifestPath),
    promotedAtUtc: new Date().toISOString()
  };
  const temporaryPath = `${pointerPath}.tmp-${process.pid}`;
  writeFileSync(temporaryPath, `${JSON.stringify(pointer, null, 2)}\n`, "utf8");
  renameSync(temporaryPath, pointerPath);
}

function resolveRepoFile(value) {
  if (typeof value !== "string" || path.isAbsolute(value)) {
    throw new Error("manifest 路径必须是仓库内相对路径。");
  }
  const resolved = path.resolve(repoRoot, value);
  const prefix = `${repoRoot}${path.sep}`;
  if (resolved !== repoRoot && !resolved.startsWith(prefix)) {
    throw new Error(`路径越过仓库边界：${value}`);
  }
  return resolved;
}

function runGit(args) {
  return execFileSync("git", args, {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true
  });
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8").replace(/^\uFEFF/u, ""));
}

function sha256File(filePath) {
  return sha256(readFileSync(filePath));
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex").toUpperCase();
}

function normalize(value) {
  return value.replaceAll("\\", "/");
}
