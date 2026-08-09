import { randomUUID } from "node:crypto";
import {
  mkdirSync,
  rmSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

import { afterEach, describe, expect, it } from "vitest";

const repoRoot = path.resolve(process.cwd(), "..", "..");
const temporaryRoots: string[] = [];

afterEach(() => {
  for (const target of temporaryRoots.splice(0)) {
    rmSync(target, { force: true, recursive: true });
  }
});

describe("release manifest", () => {
  it("生成并校验测试通道 manifest，制品变化后失败", () => {
    const relativeRoot = `test-results/release-manifest-${randomUUID()}`;
    const fullRoot = path.join(repoRoot, relativeRoot);
    temporaryRoots.push(fullRoot);
    mkdirSync(fullRoot, { recursive: true });

    const artifactPath = `${relativeRoot}/artifact.bin`;
    const evidencePath = `${relativeRoot}/desktop-active.json`;
    const manifestPath = `${relativeRoot}/release-manifest.json`;
    writeFileSync(path.join(repoRoot, artifactPath), "artifact-v1", "utf8");
    writeFileSync(
      path.join(repoRoot, evidencePath),
      JSON.stringify({
        id: "desktop-active",
        command: "npm --prefix apps/desktop run test",
        exitCode: 0,
        tests: 1,
        startedAt: "2026-08-02T00:00:00Z",
        completedAt: "2026-08-02T00:00:01Z"
      }),
      "utf8"
    );

    expect(run("scripts/create-release-manifest.mjs", [
      "--channel",
      "test",
      "--output",
      manifestPath,
      "--test-evidence",
      evidencePath,
      "--artifact",
      `sample=${artifactPath}`
    ]).status).toBe(0);
    expect(run("scripts/verify-release-manifest.mjs", [
      "--manifest",
      manifestPath
    ]).status).toBe(0);

    writeFileSync(path.join(repoRoot, artifactPath), "tampered", "utf8");
    const tampered = run("scripts/verify-release-manifest.mjs", [
      "--manifest",
      manifestPath
    ]);
    expect(tampered.status).toBe(1);
    expect(tampered.stderr).toContain("制品大小或哈希不一致");
  });
});

function run(script: string, args: string[]) {
  return spawnSync(process.execPath, [path.join(repoRoot, script), ...args], {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true
  });
}
