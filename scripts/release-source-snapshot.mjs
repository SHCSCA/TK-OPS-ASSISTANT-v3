import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";


export function collectSourceSnapshot(repoRoot) {
  const commit = runGit(repoRoot, ["rev-parse", "HEAD"]).toString("utf8").trim();
  const tree = runGit(repoRoot, ["rev-parse", "HEAD^{tree}"])
    .toString("utf8")
    .trim();
  const status = runGit(repoRoot, [
    "status",
    "--porcelain=v1",
    "--untracked-files=all"
  ]);
  const trackedDiff = runGit(repoRoot, [
    "diff",
    "--binary",
    "--no-ext-diff",
    "HEAD"
  ]);
  const untrackedContentSha256 = hashUntrackedFiles(repoRoot);
  const trackedDiffSha256 = sha256(trackedDiff);
  const sourceSnapshotSha256 = sha256(Buffer.from([
    commit,
    tree,
    trackedDiffSha256,
    untrackedContentSha256
  ].join("\0"), "utf8"));
  return {
    commit,
    tree,
    dirty: status.toString("utf8").trim().length > 0,
    statusSha256: sha256(status),
    trackedDiffSha256,
    untrackedContentSha256,
    sourceSnapshotSha256
  };
}


function hashUntrackedFiles(repoRoot) {
  const output = runGit(repoRoot, [
    "ls-files",
    "--others",
    "--exclude-standard",
    "-z"
  ]);
  const relativePaths = output
    .toString("utf8")
    .split("\0")
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right, "en"));
  const digest = createHash("sha256");
  for (const relativePath of relativePaths) {
    const fullPath = resolveTrackedPath(repoRoot, relativePath);
    digest.update(relativePath.replaceAll("\\", "/"), "utf8");
    digest.update("\0", "utf8");
    digest.update(sha256(readFileSync(fullPath)), "utf8");
    digest.update("\0", "utf8");
  }
  return digest.digest("hex").toUpperCase();
}


function resolveTrackedPath(repoRoot, relativePath) {
  const resolved = path.resolve(repoRoot, relativePath);
  if (!resolved.startsWith(`${repoRoot}${path.sep}`)) {
    throw new Error(`Git 未跟踪路径越过仓库边界：${relativePath}`);
  }
  return resolved;
}


function runGit(repoRoot, args) {
  return execFileSync("git", args, {
    cwd: repoRoot,
    encoding: "buffer",
    windowsHide: true,
    maxBuffer: 128 * 1024 * 1024
  });
}


function sha256(value) {
  return createHash("sha256").update(value).digest("hex").toUpperCase();
}
