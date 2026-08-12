import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];

function requirePath(path) {
  if (!existsSync(resolve(root, path))) {
    failures.push(`Missing required path: ${path}`);
  }
}

function requireText(path, text) {
  const absolutePath = resolve(root, path);
  if (!existsSync(absolutePath) || !readFileSync(absolutePath, "utf8").includes(text)) {
    failures.push(`Missing required content in ${path}: ${text}`);
  }
}

function read(path) {
  return readFileSync(resolve(root, path), "utf8");
}

for (const path of [
  "backend",
  "frontend",
  "agents",
  "tools",
  "memory",
  "models",
  "plugins",
  "configs",
  "docs",
  "tests",
  "scripts",
  "docker",
  ".opencode",
]) {
  requirePath(path);
}

for (const path of [
  "AGENTS.md",
  "README.md",
  "LICENSE",
  ".env.example",
  ".gitignore",
  "opencode.json",
  "docs/PROJECT_STATUS.md",
  "docs/ARCHITECTURE.md",
  "docs/ROADMAP.md",
  "docs/SECURITY.md",
  "docs/DEVELOPMENT.md",
  "docs/TESTING.md",
  "docs/phases/PHASE_01_FOUNDATION.md",
  ".opencode/commands/phase-1.md",
]) {
  requirePath(path);
}

for (const [path, text] of [
  ["LICENSE", "Apache License"],
  ["AGENTS.md", "Local-first by default."],
  [".gitignore", "*.sqlite3"],
  [".env.example", "AGENTGRAPH_OPENCODE_BASE_URL="],
  ["configs/models.yaml", "qwen3-4b-nothink:latest"],
  ["configs/models.yaml", "qwen3:4B"],
  ["configs/models.yaml", "qwen3:0.6B"],
  ["docs/phases/PHASE_01_FOUNDATION.md", "## Verification Gate"],
  ["docs/SECURITY.md", "OpenCode remains the owner of its provider authentication"],
  ["docs/PROJECT_STATUS.md", "Foundation | DONE"],
  ["docs/ROADMAP.md", "**Status:** DONE."],
]) {
  requireText(path, text);
}

let packageConfig;
let opencodeConfig;

try {
  packageConfig = JSON.parse(read("package.json"));
} catch {
  failures.push("Invalid JSON: package.json");
}

try {
  opencodeConfig = JSON.parse(read("opencode.json"));
} catch {
  failures.push("Invalid JSON: opencode.json");
}

if (!["node scripts/check-phase3.mjs", "node scripts/check-phase4.mjs"].includes(packageConfig?.scripts?.check)) {
  failures.push("package.json must run a supported project check through pnpm check");
}

for (const entry of [".env", ".env.*", ".envrc", "credentials/", "secrets/", "*.pem", "*.key"]) {
  requireText(".gitignore", entry);
}

const watcherIgnore = opencodeConfig?.watcher?.ignore;
if (!Array.isArray(watcherIgnore)) {
  failures.push("opencode.json must define watcher.ignore");
} else {
  for (const entry of [
    "**/.env",
    "**/.env.*",
    "**/.envrc",
    "**/credentials/**",
    "**/secrets/**",
    "**/*.pem",
    "**/*.key",
  ]) {
    if (!watcherIgnore.includes(entry)) {
      failures.push(`opencode.json watcher.ignore must include ${entry}`);
    }
  }
}

for (const line of read(".env.example").split("\n")) {
  if (!line.startsWith("#") && /^[A-Z0-9_]+=.+$/.test(line)) {
    failures.push(".env.example must not contain secret or configured values");
    break;
  }
}

const modelConfiguration = read("configs/models.yaml");
if (/api[_-]?key|authorization|password|token/i.test(modelConfiguration)) {
  failures.push("configs/models.yaml must not contain credentials");
}

if (failures.length > 0) {
  console.error("Foundation check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exitCode = 1;
} else {
  console.log("Foundation check passed.");
}
