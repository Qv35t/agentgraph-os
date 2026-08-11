import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

for (const path of [
  "backend/pyproject.toml",
  "backend/alembic.ini",
  "backend/alembic/versions/20260811_0001_backend_core.py",
  "backend/agentgraph/app.py",
  "backend/tests/test_lifecycle.py",
]) {
  if (!existsSync(resolve(root, path))) {
    console.error(`Missing required Phase 2 file: ${path}`);
    process.exit(1);
  }
}

const checks = [
  [process.execPath, ["scripts/check-foundation.mjs"]],
  ["uv", ["run", "--directory", "backend", "ruff", "check", "."]],
  ["uv", ["run", "--directory", "backend", "mypy"]],
  ["uv", ["run", "--directory", "backend", "pytest"]],
];

for (const [command, args] of checks) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit" });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log("Phase 2 check passed.");
