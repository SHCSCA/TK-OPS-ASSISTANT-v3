import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  cpSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { attachP0HReleaseEvidence } from "./attach-p0-h-release-evidence.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const rootPackage = JSON.parse(readFileSync(path.join(repoRoot, "package.json"), "utf8"));
const options = parseArgs(process.argv.slice(2));
const releaseRoot = path.join(
  repoRoot,
  "dist",
  "releases",
  rootPackage.version,
  "windows-x86_64"
);
const evidenceRoot = path.join(releaseRoot, "evidence");
const artifactRoot = path.join(releaseRoot, "artifacts");
const manifestPath = path.join(releaseRoot, "release-manifest.json");

try {
  assertReleaseRoot(releaseRoot);
  mkdirSync(evidenceRoot, { recursive: true });
  mkdirSync(artifactRoot, { recursive: true });
  if (options.targetAiEvidence) {
    attachP0HReleaseEvidence({ channel: options.channel, evidencePath: options.targetAiEvidence, evidenceRoot, manifestPath, repoRoot, version: rootPackage.version });
    runNode("verify-manifest", ["scripts/verify-release-manifest.mjs", "--manifest", normalize(path.relative(repoRoot, manifestPath)), ...(options.promote ? ["--promote"] : [])]);
    console.log(`[windows-release] H5 证据已附加：manifest=${normalize(path.relative(repoRoot, manifestPath))}`);
    process.exit(0);
  }

  runCommand("version-check", "npm", ["run", "version:check"]);
  const evidence = [
    runCommand(
      "runtime-full",
      "npm",
      ["run", "test:runtime"],
      true
    ),
    runCommand(
      "desktop-active",
      "npm",
      ["--prefix", "apps/desktop", "run", "test"],
      true
    ),
    runCommand(
      "desktop-typecheck",
      "npm",
      ["--prefix", "apps/desktop", "run", "typecheck"],
      true
    ),
    runCommand(
      "rust-tauri",
      "cargo",
      ["test", "--manifest-path", "apps/desktop/src-tauri/Cargo.toml"],
      true
    ),
    runCommand(
      "playwright-first-run",
      "npm",
      ["--prefix", "apps/desktop", "run", "test:e2e"],
      true
    ),
    runCommand(
      "playwright-account-workspace",
      "npm",
      ["--prefix", "apps/desktop", "run", "test:e2e:compat"],
      true
    )
  ];

  runCommand("prepare-sidecar", "npm", ["run", "runtime:sidecar:prepare"]);
  evidence.push(
    runCommand(
      "sidecar-smoke",
      "npm",
      ["run", "test:sidecar-smoke"],
      true
    )
  );
  const tauriBuildArgs = [
    path.join(
      repoRoot,
      "apps",
      "desktop",
      "node_modules",
      "@tauri-apps",
      "cli",
      "tauri.js"
    ),
    "build"
  ];
  if (options.channel === "test") {
    tauriBuildArgs.push(
      "--config",
      "src-tauri/tauri.test.conf.json"
    );
  }
  runCommand(
    "tauri-build",
    process.execPath,
    tauriBuildArgs,
    false,
    {},
    path.join(repoRoot, "apps", "desktop")
  );

  const assembled = assembleArtifacts();
  const artifacts = assembled.artifacts;
  const guiSmokeEvidence = options.guiSmokeEvidence
    || runGuiSmoke(assembled.desktopBinary, artifacts.portable);
  evidence.push(
    validateExternalEvidence(
      guiSmokeEvidence,
      assembled.desktopBinary,
      artifacts.portable
    )
  );
  evidence.push(runInstallerSmoke(assembled.installerBinary));
  evidence.push(runPackagedLicenseActivation(assembled));
  if (options.targetTikTokEvidence) {
    evidence.push(
      validateTargetTikTokEvidence(options.targetTikTokEvidence, assembled)
    );
  }
  const relativeManifest = normalize(path.relative(repoRoot, manifestPath));
  const createArgs = [
    "scripts/create-release-manifest.mjs",
    "--channel",
    options.channel,
    "--output",
    relativeManifest
  ];
  for (const item of evidence) {
    createArgs.push("--test-evidence", item);
  }
  for (const [kind, artifactPath] of Object.entries(artifacts)) {
    createArgs.push(
      "--artifact",
      `${kind}=${normalize(path.relative(repoRoot, artifactPath))}`
    );
  }
  runNode("create-manifest", createArgs);

  const verifyArgs = [
    "scripts/verify-release-manifest.mjs",
    "--manifest",
    relativeManifest
  ];
  if (options.promote) verifyArgs.push("--promote");
  runNode("verify-manifest", verifyArgs);
  console.log(
    `[windows-release] 完成：channel=${options.channel} `
    + `manifest=${relativeManifest} promoted=${options.promote}`
  );
} catch (error) {
  console.error(
    `[windows-release] 失败：${error instanceof Error ? error.message : "未知错误"}`
  );
  process.exitCode = 1;
}

function parseArgs(args) {
  const channelIndex = args.indexOf("--channel");
  const channel = channelIndex >= 0 ? args[channelIndex + 1] : "test";
  if (!new Set(["test", "production"]).has(channel)) {
    throw new Error("--channel 只允许 test 或 production。");
  }
  const evidenceIndex = args.indexOf("--gui-smoke-evidence");
  const guiSmokeEvidence = evidenceIndex >= 0 ? args[evidenceIndex + 1] : "";
  const targetIndex = args.indexOf("--target-tiktok-evidence");
  const targetTikTokEvidence = targetIndex >= 0 ? args[targetIndex + 1] : "";
  const aiIndex = args.indexOf("--target-ai-evidence");
  const targetAiEvidence = aiIndex >= 0 ? args[aiIndex + 1] : "";
  if (aiIndex >= 0 && (!targetAiEvidence || targetAiEvidence.startsWith("--"))) throw new Error("--target-ai-evidence 缺少值。");
  const promote = args.includes("--promote");
  if (promote && (channel !== "production" || !targetAiEvidence)) {
    throw new Error("提升 current 必须使用 production、TikTok 登录与 P0-H 真实 Provider 证据。" );
  }
  return { channel, guiSmokeEvidence, targetTikTokEvidence, targetAiEvidence, promote };
}

function runCommand(
  id,
  command,
  args,
  createEvidence = false,
  artifactBindings = {},
  cwd = repoRoot
) {
  const startedAt = new Date().toISOString();
  const result = spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 32 * 1024 * 1024,
    shell: process.platform === "win32"
  });
  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  if (result.error || result.status !== 0) {
    throw new Error(`${id} 失败，退出码 ${result.status ?? "unknown"}。`);
  }
  if (!createEvidence) return "";
  const evidencePath = path.join(evidenceRoot, `${id}.json`);
  const document = {
    id,
    command: [command, ...args].join(" "),
    exitCode: 0,
    tests: extractTestCount(`${result.stdout || ""}\n${result.stderr || ""}`),
    startedAt,
    completedAt: new Date().toISOString(),
    stdoutSha256: sha256(Buffer.from(result.stdout || "", "utf8")),
    stderrSha256: sha256(Buffer.from(result.stderr || "", "utf8")),
    artifactBindings
  };
  writeFileSync(evidencePath, `${JSON.stringify(document, null, 2)}\n`, "utf8");
  return normalize(path.relative(repoRoot, evidencePath));
}

function runNode(id, args) {
  const result = spawnSync(process.execPath, args, {
    cwd: repoRoot,
    encoding: "utf8",
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024
  });
  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  if (result.error || result.status !== 0) {
    throw new Error(`${id} 失败，退出码 ${result.status ?? "unknown"}。`);
  }
}

function assembleArtifacts() {
  const targetRoot = path.join(repoRoot, "apps", "desktop", "src-tauri", "target", "release");
  const desktopBinary = requiredFile(path.join(targetRoot, "tk-ops-desktop.exe"));
  const sidecarBinary = requiredFile(
    path.join(
      repoRoot,
      "apps",
      "desktop",
      "src-tauri",
      "binaries",
      "tk-ops-runtime-x86_64-pc-windows-msvc.exe"
    )
  );
  const installerSource = findLatestInstaller(path.join(targetRoot, "bundle", "nsis"));

  const sidecarArtifact = path.join(artifactRoot, "tk-ops-runtime.exe");
  const installerArtifact = path.join(artifactRoot, path.basename(installerSource));
  copyFileSync(sidecarBinary, sidecarArtifact);
  copyFileSync(installerSource, installerArtifact);

  const portableParent = path.join(releaseRoot, "portable");
  const portableName = `TK-OPS-${rootPackage.version}-windows-x86_64`;
  const portableRoot = path.join(portableParent, portableName);
  assertReleaseRoot(portableRoot);
  rmSync(portableRoot, { force: true, recursive: true });
  mkdirSync(portableRoot, { recursive: true });
  const portableDesktopBinary = path.join(portableRoot, "tk-ops-desktop.exe");
  copyFileSync(desktopBinary, portableDesktopBinary);
  cpSync(
    path.join(repoRoot, "apps", "desktop", "src-tauri", "resources"),
    path.join(portableRoot, "resources"),
    { recursive: true }
  );
  copyFileSync(
    sidecarBinary,
    path.join(portableRoot, "resources", "runtime", "tk-ops-runtime.exe")
  );
  writeFileSync(
    path.join(portableRoot, "使用说明.txt"),
    "TK-OPS 免安装运行包\r\n\r\n双击 tk-ops-desktop.exe 启动。\r\n"
      + "应用数据仍保存在 Windows 本地应用数据目录，本包不是数据随身版。\r\n",
    "utf8"
  );
  const portableZip = path.join(artifactRoot, `${portableName}-portable.zip`);
  rmSync(portableZip, { force: true });
  const archive = spawnSync(
    "tar",
    ["-a", "-c", "-f", portableZip, "-C", portableParent, portableName],
    { cwd: repoRoot, encoding: "utf8", windowsHide: true }
  );
  if (archive.error || archive.status !== 0) {
    throw new Error(`免安装包压缩失败：${archive.stderr || "未知错误"}`);
  }
  requiredFile(portableZip);
  const desktopArtifact = path.join(artifactRoot, "tk-ops-desktop.exe");
  copyFileSync(desktopBinary, desktopArtifact);
  return {
    desktopBinary: portableDesktopBinary,
    installerBinary: installerArtifact,
    runtimeManifest: requiredFile(
      path.join(
        portableRoot,
        "resources",
        "runtime",
        "tk-ops-runtime.manifest.json"
      )
    ),
    sidecarBinary: sidecarArtifact,
    artifacts: {
      desktop: desktopArtifact,
      sidecar: sidecarArtifact,
      installer: installerArtifact,
      portable: portableZip
    }
  };
}

function runInstallerSmoke(installerBinary) {
  return runCommand(
    "windows-installer-smoke",
    "powershell",
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      "tests/packaging/windows-installer-smoke-runner.ps1",
      "-ScriptPath",
      path.join(
        repoRoot,
        "tests",
        "packaging",
        "windows-installer-smoke.ps1"
      ),
      "-InstallerPath",
      installerBinary
    ],
    true,
    { installer: sha256(readFileSync(installerBinary)) }
  );
}

function runPackagedLicenseActivation(assembled) {
  const evidencePath = path.join(evidenceRoot, "packaged-license-activation.json");
  runNode("packaged-license-activation", [
    "scripts/packaged-license-activation-smoke.mjs",
    "--runtime",
    normalize(path.relative(repoRoot, assembled.sidecarBinary)),
    "--runtime-manifest",
    normalize(path.relative(repoRoot, assembled.runtimeManifest)),
    "--desktop",
    normalize(path.relative(repoRoot, assembled.desktopBinary)),
    "--evidence",
    normalize(path.relative(repoRoot, evidencePath))
  ]);
  return normalize(path.relative(repoRoot, evidencePath));
}

function validateTargetTikTokEvidence(relativePath, assembled) {
  const fullPath = resolveRepoPath(relativePath);
  const evidence = JSON.parse(readFileSync(fullPath, "utf8").replace(/^\uFEFF/u, ""));
  const expectedBindings = {
    desktop: sha256(readFileSync(assembled.desktopBinary)),
    sidecar: sha256(readFileSync(assembled.sidecarBinary)),
    installer: sha256(readFileSync(assembled.installerBinary))
  };
  if (
    evidence.id !== "target-tiktok-supervised-login"
    || evidence.exitCode !== 0
    || evidence.result !== "passed"
    || !/^log_[A-Za-z0-9_-]{8,128}$/u.test(evidence.logId || "")
    || Object.entries(expectedBindings).some(
      ([kind, digest]) => evidence.artifactBindings?.[kind] !== digest
    )
  ) {
    throw new Error("目标机器 TikTok 监督登录证据无效或未绑定当前制品。" );
  }
  return normalize(path.relative(repoRoot, fullPath));
}

function runGuiSmoke(desktopBinary, portableZip) {
  const evidencePath = path.join(evidenceRoot, "windows-gui-smoke.json");
  runCommand(
    "windows-gui-smoke",
    "powershell",
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      "tests/packaging/windows-gui-smoke-runner.ps1",
      "-ScriptPath",
      path.join(repoRoot, "tests", "packaging", "windows-gui-smoke.ps1"),
      "-DesktopPath",
      desktopBinary,
      "-PortableZipPath",
      portableZip,
      "-EvidencePath",
      evidencePath
    ]
  );
  return normalize(path.relative(repoRoot, evidencePath));
}

function validateExternalEvidence(relativePath, desktopBinary, portableZip) {
  const fullPath = resolveRepoPath(relativePath);
  const evidence = JSON.parse(readFileSync(fullPath, "utf8").replace(/^\uFEFF/u, ""));
  const desktopSha256 = sha256(readFileSync(desktopBinary));
  const portableSha256 = sha256(readFileSync(portableZip));
  const requiredChecks = [
    "fresh-portable-extraction",
    "visible-main-window",
    "single-root-executable",
    "standard-window-controls",
    "minimize-maximize-restore",
    "runtime-ready",
    "single-instance",
    "graceful-close",
    "restart-recovery"
  ];
  if (
    evidence.id !== "windows-gui-smoke"
    || evidence.exitCode !== 0
    || evidence.desktopSha256 !== desktopSha256
    || evidence.portableSha256 !== portableSha256
    || !Array.isArray(evidence.checks)
    || requiredChecks.some((check) => !evidence.checks.includes(check))
  ) {
    throw new Error("GUI smoke 证据 ID 或退出码无效。" );
  }
  return normalize(path.relative(repoRoot, fullPath));
}

function findLatestInstaller(directory) {
  const candidates = readdirSync(directory)
    .filter((name) => name.endsWith("-setup.exe"))
    .map((name) => path.join(directory, name))
    .sort((left, right) => statSync(right).mtimeMs - statSync(left).mtimeMs);
  if (candidates.length === 0) throw new Error("没有找到 NSIS 安装包。" );
  return requiredFile(candidates[0]);
}

function requiredFile(filePath) {
  const stat = statSync(filePath);
  if (!stat.isFile() || stat.size <= 0) throw new Error(`制品不存在或为空：${filePath}`);
  return filePath;
}

function resolveRepoPath(value) {
  const resolved = path.resolve(repoRoot, value);
  if (!resolved.startsWith(`${repoRoot}${path.sep}`)) {
    throw new Error(`路径越过仓库边界：${value}`);
  }
  return resolved;
}

function assertReleaseRoot(target) {
  const releaseBase = path.join(repoRoot, "dist", "releases");
  const resolved = path.resolve(target);
  if (!resolved.startsWith(`${releaseBase}${path.sep}`)) {
    throw new Error(`发布路径越过受控目录：${target}`);
  }
}

function extractTestCount(output) {
  const normalizedOutput = output.replace(/\u001B\[[0-?]*[ -/]*[@-~]/gu, "");
  const suiteMatches = [
    ...normalizedOutput.matchAll(
      /Tests\s+(?:\d+\s+failed\s*\|\s*)?(\d+)\s+passed/gu
    )
  ];
  if (suiteMatches.length > 0) return Number(suiteMatches.at(-1)[1]);
  const runnerMatches = [
    ...normalizedOutput.matchAll(
      /^[= \t]*(\d+)\s+passed(?:,[^\r\n]+)?\s+in\s+/gmu
    ),
    ...normalizedOutput.matchAll(
      /test result:\s+ok\.\s+(\d+)\s+passed;/gu
    ),
    ...normalizedOutput.matchAll(
      /^\s*(\d+)\s+passed(?:\s+\(|\s*$)/gmu
    )
  ].map((match) => Number(match[1]));
  return runnerMatches.length > 0 ? Math.max(...runnerMatches) : null;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex").toUpperCase();
}

function normalize(value) {
  return value.replaceAll("\\", "/");
}
