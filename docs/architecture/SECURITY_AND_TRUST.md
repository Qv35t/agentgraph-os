# Security and Trust Target

Status: approved target architecture. Current services remain loopback-only, remote control is disabled by default, and approvals are process-local.

## Remote Trust

Future remote access requires strong identity and session management, with passkeys/WebAuthn, second factor where appropriate, trusted-device levels, revocation, rate limiting, audit, and secure recovery. An unknown or limited device must not receive privileged terminal control, sensitive secrets, sudo, or unrestricted Remote View. Server-side authorization remains authoritative.

## Approvals and Grants

Approval is a first-class durable domain entity. It identifies the requested action, agent, task, goal, target device, reason, risk, scope, and expiry. Future actions are allow once, allow for this task, reject, and modify. A Grant is scoped to a task and capability, has an expiry, is auditable/revocable, and cannot transfer or expand itself. Baseline approval-required actions include sudo, package/OS changes, data deletion, external messages or publishing, Git push/merge, account/security changes, reboot/shutdown, secret permission changes, and irreversible external effects.

## Secrets and Lockdown

A future credential broker/vault performs a permitted scoped operation without normally revealing raw credentials to an agent. Credential use records identity, principal, task, action, target, time, and result, never the secret value. Emergency lockdown must revoke remote sessions and temporary grants, cancel or pause privileged work, disable remote command execution, preserve audit history, and retain a local administrative recovery route. Running agents must re-check authorization at action boundaries so a prior grant cannot bypass lockdown.

See [`../SECURITY.md`](../SECURITY.md), [`REMOTE_INTERFACES.md`](REMOTE_INTERFACES.md), and ADR-0007.
