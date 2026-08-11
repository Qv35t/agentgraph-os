# Installing this documentation pack

The pack is designed to be extracted into the **root of the existing `agentgraph-os` repository**.

It intentionally includes a replacement/enhanced:

- `AGENTS.md` (new);
- `docs/ARCHITECTURE.md`;
- `docs/ROADMAP.md`;
- additional docs/rules/phases/ADRs;
- `.opencode/commands/` and `.opencode/agents/`;
- minimal `opencode.json`.

Before replacing an existing `opencode.json`, merge it if you already have project-specific provider/model/MCP settings.

After copying, review:

```bash
git status --short
git diff -- AGENTS.md docs .opencode opencode.json
```

Then start OpenCode in the repository root and use:

```text
/project-status
/phase-2
```

Do not run `/init` after installing unless you intentionally want OpenCode to rewrite/improve AGENTS.md. If you do run `/init`, review its diff carefully because this pack uses a deliberate lazy-context routing design.
