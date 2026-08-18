# Phase 11A - Durable Security Foundation

Status: PARTIAL. The durable authentication/security foundation and automated
regression gate are present, but controlled tools and the existing Approvals UI
still use the prior process-local approval service. Manual acceptance must not
begin until that single-source-of-truth migration is complete.

Implemented: durable users, devices, hashed cookie sessions, WebAuthn
challenges/passkeys, encrypted TOTP and vault storage, server-side CSRF,
durable approvals/grants/audit/lockdown records, and a Security workspace.

Boundaries: the service remains loopback-first. No WAN access, distributed
identity, credential provider integration, scheduler, failover, automatic run
recovery, or agent autonomy is introduced.
