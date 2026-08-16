# AgentGraph OS — Security Baseline

## Network

- Bind application servers to `127.0.0.1` by default.
- Do not expose Ollama/OpenCode/AgentGraph directly to LAN/WAN by default.
- External access requires a separate explicit security design.

## Secrets

Never commit or persist:

- `.env` with real values;
- API keys;
- OAuth access/refresh tokens;
- copied OpenCode auth files;
- Basic Auth passwords;
- Authorization headers;
- private keys.

Redact secrets from errors/logs. `.env.example` contains empty placeholders only.

## OpenCode auth boundary

When AgentGraph uses a local OpenCode Server as a model bridge, OpenCode remains the owner of its provider authentication. AgentGraph must not read or copy OpenCode's OAuth credential store.

## Model output boundary

Treat all model/provider output as untrusted text.

Do not:

- run shell commands because a model printed them;
- execute code blocks automatically;
- interpret arbitrary JSON as a tool call without validation/policy;
- permit file/network/OS actions implicitly.

## Unsafe mechanisms prohibited

- `eval`/`exec` for model/user payloads;
- unsafe pickle deserialization;
- arbitrary shell concatenation;
- `verify=False` / disabled TLS checks;
- logging complete raw provider bodies when they may contain secrets;
- returning internal stack traces to API clients.

## Tool security

Phase 6 tools require typed input, allowlist/policy, timeouts, cancellation,
bounded output, audit metadata, and per-tool security review. The current
registry is disabled by default and contains `system.current_time` plus the
approval-gated, allowlisted `desktop.open_application`; shell access does not
exist.
