import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, extname, resolve } from "node:path";
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

for (const file of markdownFiles(resolve(root, "docs"))) {
  for (const target of readFileSync(file, "utf8").matchAll(/\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)/g)) {
    if (!target[1].includes(":") && !existsSync(resolve(dirname(file), target[1]))) {
      throw new Error(`Broken local documentation link: ${file} -> ${target[1]}`);
    }
  }
}
console.log("Phase 10 check passed.");

function* markdownFiles(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) yield* markdownFiles(path);
    else if (extname(entry.name) === ".md") yield path;
  }
}
