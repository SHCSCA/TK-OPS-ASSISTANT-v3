import { createHash } from "node:crypto";
import {
  readFileSync,
  renameSync,
  statSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import process from "node:process";

import {
  p0hRealProviderEvidenceId,
  prepareP0HReleaseEvidence
} from "./p0-h-real-provider-evidence.mjs";

export function attachP0HReleaseEvidence({
  channel,
  evidencePath,
  evidenceRoot,
  manifestPath,
  repoRoot,
  version
}) {
  const manifest = readJson(manifestPath);
  validateManifestIdentity(manifest, { channel, version });
  const artifacts = resolveAndVerifyArtifacts(manifest, repoRoot);
  const wrapperPath = prepareP0HReleaseEvidence({
    artifacts,
    evidencePath: path.resolve(repoRoot, evidencePath),
    evidenceRoot,
    repoRoot,
    version
  });
  const wrapper = readJson(path.resolve(repoRoot, wrapperPath));
  const evidenceEntry = {
    id: p0hRealProviderEvidenceId,
    command: String(wrapper.command),
    exitCode: 0,
    tests: 1,
    startedAt: String(wrapper.startedAt),
    completedAt: String(wrapper.completedAt),
    evidencePath: wrapperPath,
    evidenceSha256: sha256File(path.resolve(repoRoot, wrapperPath)),
    artifactBindings: wrapper.artifactBindings
  };
  manifest.tests = [
    ...manifest.tests.filter((item) => item.id !== p0hRealProviderEvidenceId),
    evidenceEntry
  ];
  writeJsonAtomic(manifestPath, manifest);
}

function validateManifestIdentity(manifest, expected) {
  if (
    manifest?.schemaVersion !== 2
    || manifest.version !== expected.version
    || manifest.channel !== expected.channel
    || !Array.isArray(manifest.tests)
    || !Array.isArray(manifest.artifacts)
  ) {
    throw new Error("当前 Release Manifest 与待附加的 H5 证据不匹配。");
  }
}

function resolveAndVerifyArtifacts(manifest, repoRoot) {
  const entries = Object.fromEntries(
    manifest.artifacts.map((item) => [item.kind, item])
  );
  return Object.fromEntries(
    ["desktop", "sidecar", "installer", "portable"].map((kind) => {
      const entry = entries[kind];
      if (!entry || typeof entry.path !== "string") {
        throw new Error(`Release Manifest 缺少 ${kind} 制品。`);
      }
      const filePath = resolveInside(repoRoot, entry.path);
      const stat = statSync(filePath);
      if (
        !stat.isFile()
        || stat.size !== entry.size
        || sha256File(filePath) !== String(entry.sha256).toUpperCase()
      ) {
        throw new Error(`${kind} 制品与 Release Manifest 不一致。`);
      }
      return [kind, filePath];
    })
  );
}

function resolveInside(root, relativePath) {
  if (path.isAbsolute(relativePath)) throw new Error("制品路径必须是仓库内相对路径。");
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(resolvedRoot, relativePath);
  if (!resolved.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error("制品路径越过仓库边界。");
  }
  return resolved;
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8").replace(/^\uFEFF/u, ""));
}

function writeJsonAtomic(filePath, value) {
  const temporaryPath = `${filePath}.tmp-${process.pid}`;
  writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  renameSync(temporaryPath, filePath);
}

function sha256File(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex").toUpperCase();
}
