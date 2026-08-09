import { createHash } from "node:crypto";
import {
  lstat,
  readdir,
  readFile
} from "node:fs/promises";
import { join, relative, resolve } from "node:path";

const ignoredDirectoryNames = new Set([
  "__pycache__",
  ".mypy_cache",
  ".pytest_cache"
]);
const ignoredFileSuffixes = [".pyc", ".pyo"];

export async function computeRuntimeSourceSha256(runtimeRoot) {
  const resolvedRoot = resolve(runtimeRoot);
  const inputs = [
    join(resolvedRoot, "src"),
    join(resolvedRoot, "alembic"),
    join(resolvedRoot, "alembic.ini"),
    join(resolvedRoot, "pyproject.toml"),
    join(resolvedRoot, "resources"),
    join(resolvedRoot, "packaging", "tk_ops_runtime.spec")
  ];
  const files = [];
  for (const input of inputs) {
    await collectInputFiles(input, files);
  }
  files.sort((left, right) => {
    const leftPath = portableRelativePath(resolvedRoot, left);
    const rightPath = portableRelativePath(resolvedRoot, right);
    return leftPath < rightPath ? -1 : leftPath > rightPath ? 1 : 0;
  });

  const digest = createHash("sha256");
  for (const file of files) {
    const sourcePath = portableRelativePath(resolvedRoot, file);
    const pathBytes = Buffer.from(sourcePath, "utf8");
    const content = await readFile(file);
    digest.update("tk-ops-source-v1\0", "utf8");
    digest.update(`${pathBytes.length}\0`, "utf8");
    digest.update(pathBytes);
    digest.update(`${content.length}\0`, "utf8");
    digest.update(content);
  }
  return digest.digest("hex").toUpperCase();
}

async function collectInputFiles(input, files) {
  const metadata = await lstat(input);
  if (metadata.isSymbolicLink()) {
    throw new Error("Runtime 构建输入不允许使用符号链接");
  }
  if (metadata.isFile()) {
    if (!isIgnoredFile(input)) {
      files.push(input);
    }
    return;
  }
  if (!metadata.isDirectory()) {
    throw new Error("Runtime 构建输入包含不受支持的文件类型");
  }

  const entries = await readdir(input, { withFileTypes: true });
  entries.sort((left, right) => (
    left.name < right.name ? -1 : left.name > right.name ? 1 : 0
  ));
  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectoryNames.has(entry.name)) {
      continue;
    }
    if (entry.isSymbolicLink()) {
      throw new Error("Runtime 构建输入不允许使用符号链接");
    }
    const child = join(input, entry.name);
    if (entry.isDirectory()) {
      await collectInputFiles(child, files);
    } else if (entry.isFile() && !isIgnoredFile(child)) {
      files.push(child);
    } else if (!entry.isFile()) {
      throw new Error("Runtime 构建输入包含不受支持的文件类型");
    }
  }
}

function isIgnoredFile(path) {
  const normalized = path.toLowerCase();
  return ignoredFileSuffixes.some((suffix) => normalized.endsWith(suffix));
}

function portableRelativePath(root, path) {
  const normalized = relative(root, path).replaceAll("\\", "/");
  if (
    !normalized
    || normalized === ".."
    || normalized.startsWith("../")
  ) {
    throw new Error("Runtime 构建输入超出受控目录");
  }
  return normalized;
}
