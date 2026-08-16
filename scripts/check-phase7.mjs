import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const commands = [
  ["pnpm", ["--dir", "frontend", "check"]],
  ["uv", ["run", "--directory", "backend", "ruff", "check", "."]],
  ["uv", ["run", "--directory", "backend", "mypy", "agentgraph", "tests"]],
  ["uv", ["run", "--directory", "backend", "pytest"]],
];

for (const [command, args] of commands) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit" });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log("Phase 7 check passed.");
