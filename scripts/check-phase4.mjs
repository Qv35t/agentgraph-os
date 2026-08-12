import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const checks = [
  [process.execPath, ["scripts/check-phase3.mjs"]],
  ["pnpm", ["--dir", "frontend", "check"]],
];

for (const [command, args] of checks) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit" });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

console.log("Phase 4 check passed.");
