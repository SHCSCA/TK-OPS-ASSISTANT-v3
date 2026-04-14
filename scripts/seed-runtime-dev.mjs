import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const runtimeSrc = path.join(repoRoot, "apps", "py-runtime", "src");
const venvPython = path.join(repoRoot, "venv", "Scripts", "python.exe");
const python = process.env.TK_OPS_PYTHON || (existsSync(venvPython) ? venvPython : "python");

const result = spawnSync(
  python,
  ["-m", "devtools.seed_data", ...process.argv.slice(2)],
  {
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH
        ? `${runtimeSrc}${path.delimiter}${process.env.PYTHONPATH}`
        : runtimeSrc,
    },
    stdio: "inherit",
  },
);

process.exit(result.status ?? 1);
