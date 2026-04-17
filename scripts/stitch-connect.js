const { spawnSync } = require("node:child_process");
const data = { title: "TK-OPS UI Lab" };
const args = ["/d", "/s", "/c", "npx", "-y", "@_davideast/stitch-mcp", "tool", "create_project", "-d", JSON.stringify(data), "-o", "json"];
const result = spawnSync(process.env.ComSpec || "cmd.exe", args, { encoding: "utf8", maxBuffer: 1024 * 1024 * 20 });
process.stdout.write(result.stdout || "");
process.stderr.write(result.stderr || "");
process.exit(result.status ?? 1);
