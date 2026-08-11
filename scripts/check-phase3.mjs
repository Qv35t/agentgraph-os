import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

for (const path of [
  "backend/agentgraph/models/router.py",
  "backend/agentgraph/providers/ollama.py",
  "backend/agentgraph/providers/opencode.py",
  "backend/agentgraph/providers/openai_compatible.py",
  "backend/alembic/versions/20260811_0002_model_metadata.py",
  "backend/tests/test_models.py",
]) {
  if (!existsSync(resolve(root, path))) {
    console.error(`Missing required Phase 3 file: ${path}`);
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

console.log("Phase 3 check passed.");
