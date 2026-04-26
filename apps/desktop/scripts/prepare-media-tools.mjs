import { createHash } from "node:crypto";
import { createWriteStream } from "node:fs";
import { mkdir, rm, stat } from "node:fs/promises";
import { get } from "node:https";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";

const __dirname = dirname(fileURLToPath(import.meta.url));
const desktopRoot = resolve(__dirname, "..");
const resourcesRoot = join(desktopRoot, "src-tauri", "resources");
const ffprobeTarget = join(resourcesRoot, "bin", "ffprobe", "windows-x64", "ffprobe.exe");
const tempRoot = join(desktopRoot, ".media-tools-tmp");
const archivePath = join(tempRoot, "ffmpeg-win64-lgpl-shared.zip");
const extractDir = join(tempRoot, "extract");

const tool = {
  archiveSha256: "270D2DED388676913408874AC015600861F267732D7C083093B03479B0803EAC",
  binarySha256: "A7C5CE012983EA485C2709CE705F24FA93FF95E462C04B30F4AE74461847CE41",
  url: "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-01-31-12-57/ffmpeg-n7.1.3-35-g419cdf9dcc-win64-lgpl-shared-7.1.zip"
};

async function main() {
  if (process.platform !== "win32") {
    log("当前只准备 Windows x64 FFprobe，非 Windows 环境跳过。");
    return;
  }

  if (await hasValidBinary()) {
    log("FFprobe 已存在且校验通过，跳过下载。");
    return;
  }

  await rm(tempRoot, { force: true, recursive: true });
  await mkdir(tempRoot, { recursive: true });
  await mkdir(dirname(ffprobeTarget), { recursive: true });

  try {
    log("开始下载 FFprobe 媒体工具包。");
    await downloadFile(tool.url, archivePath);
    await assertHash(archivePath, tool.archiveSha256, "FFprobe 压缩包校验失败");
    await expandArchive(archivePath, extractDir);
    const extracted = await findExtractedFfprobe(extractDir);
    await assertHash(extracted, tool.binarySha256, "FFprobe 可执行文件校验失败");
    await rm(ffprobeTarget, { force: true });
    await mkdir(dirname(ffprobeTarget), { recursive: true });
    await copyFileWithPowerShell(extracted, ffprobeTarget);
    await assertHash(ffprobeTarget, tool.binarySha256, "FFprobe 写入后校验失败");
    log(`FFprobe 已准备完成：${ffprobeTarget}`);
  } finally {
    await rm(tempRoot, { force: true, recursive: true });
  }
}

async function hasValidBinary() {
  try {
    await stat(ffprobeTarget);
    const hash = await sha256(ffprobeTarget);
    return hash === tool.binarySha256;
  } catch {
    return false;
  }
}

function downloadFile(url, target) {
  return new Promise((resolveDownload, rejectDownload) => {
    const request = get(url, (response) => {
      if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        downloadFile(response.headers.location, target).then(resolveDownload, rejectDownload);
        return;
      }
      if (response.statusCode !== 200) {
        rejectDownload(new Error(`下载失败，HTTP ${response.statusCode}`));
        return;
      }
      const output = createWriteStream(target);
      response.pipe(output);
      output.on("finish", () => output.close(resolveDownload));
      output.on("error", rejectDownload);
    });
    request.on("error", rejectDownload);
  });
}

async function expandArchive(source, target) {
  await mkdir(target, { recursive: true });
  await runPowerShell([
    "Expand-Archive",
    "-Path",
    quote(source),
    "-DestinationPath",
    quote(target),
    "-Force"
  ].join(" "));
}

async function copyFileWithPowerShell(source, target) {
  await runPowerShell([
    "Copy-Item",
    "-LiteralPath",
    quote(source),
    "-Destination",
    quote(target),
    "-Force"
  ].join(" "));
}

function runPowerShell(command) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], {
      stdio: "inherit",
      windowsHide: true
    });
    child.on("exit", (code) => {
      if (code === 0) {
        resolveRun();
      } else {
        rejectRun(new Error(`PowerShell 命令执行失败：${command}`));
      }
    });
    child.on("error", rejectRun);
  });
}

async function findExtractedFfprobe(root) {
  const command = `Get-ChildItem -Path ${quote(root)} -Recurse -Filter ffprobe.exe | Select-Object -First 1 -ExpandProperty FullName`;
  return new Promise((resolveFind, rejectFind) => {
    const child = spawn("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], {
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("exit", (code) => {
      const found = stdout.trim();
      if (code === 0 && found) {
        resolveFind(found);
      } else {
        rejectFind(new Error(`未能从压缩包中找到 ffprobe.exe。${stderr}`));
      }
    });
    child.on("error", rejectFind);
  });
}

async function assertHash(path, expected, message) {
  const actual = await sha256(path);
  if (actual !== expected) {
    throw new Error(`${message}。期望 ${expected}，实际 ${actual}`);
  }
}

async function sha256(path) {
  const buffer = await readFile(path);
  return createHash("sha256").update(buffer).digest("hex").toUpperCase();
}

function quote(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function log(message) {
  console.log(`[media-tools] ${message}`);
}

main().catch((error) => {
  console.error(`[media-tools] ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
