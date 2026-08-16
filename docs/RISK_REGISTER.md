# Future Architecture Risk Register

Status: target-risk baseline. Mitigations are design directions, not implemented controls unless current-state documentation says otherwise.

| Risk | Impact | Mitigation direction | Planned phase |
|---|---|---|---|
| Split-brain Core | Conflicting execution or data loss | Fencing, leader lease/quorum decision, single writer, and failover tests | 9, 10 |
| Repeated side effects after recovery | Duplicate external or destructive action | Checkpoints, idempotency/external action ledger, approval on uncertainty | 10 |
| Compromised remote device | Unauthorized control or data access | Strong authentication, trust levels, revocation, least privilege, audit | 11, 17 |
| Credential leakage | Account compromise | Credential broker, redaction, scoped grants, no raw secrets in agents | 11 |
| Poisoned or stale memory | Incorrect planning or unsafe action | Provenance, confidence, review, supersession, retrieval boundaries | 13 |
| Incorrect model routing | Privacy, cost, or quality failure | Explicit profiles, enforced Local Only, visible route decisions | 13 |
| Infinite agent retries | Resource exhaustion or harmful loops | Retry budgets, escalation, cancellation, blocker report | 12, 21 |
| Concurrent OpenCode conflicts | Corrupted repository or blocked work | Ownership boundaries, isolation/worktree policy, conflict detection | 14 |
| Runaway cloud cost | Unexpected spend | Cost estimates, budgets, explicit cloud policy, usage observability | 13, 21 |
| Local Only exfiltration | Privacy breach | Deny external provider routes and payload egress | 13 |
| Semantic-index privacy | Sensitive file/memory disclosure | Opt-in indexed roots, access policy, local storage, provenance | 18 |
| Backup corruption | Unrecoverable state | Versioned encrypted backups, integrity checks, restore drills, retention | 19 |
| Silent failover failure | Extended outage or false availability | Heartbeats, promotion record, notifications, recovery tests | 9, 10 |
| Unreliable GUI automation | Incorrect external action | Prefer typed integrations; Remote View is not implicit control | 14, 17 |
| Excessive autonomous maintenance | Unauthorized system changes | Explicit scope, approval policy, temporary grants, audit | 11, 21 |
