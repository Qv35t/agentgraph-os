# Storage, Search, and Backup Target

Status: planned target. Current storage is local Phase 1-7 persistence and asset storage; unified files, semantic search, and backup/restore are not implemented.

## Unified Files and Search

The target file workspace presents registered NAS, PC, laptop, future-node, and opt-in cloud locations as a logical workspace while retaining physical location, availability, and access policy. It must never represent a remote file as local. Future search may combine name, metadata, full text, embeddings, memory links, and project relations. Indexed roots require explicit registration and privacy policy; semantic search is not permission to read or export arbitrary files.

## Backup and Recovery

Target backups cover Core data, Lexi memory, projects, goals, tasks, workflows, configuration, encrypted secret material, Run history, documentation, and registered-device metadata. A compatible replacement machine should restore as much as is locally recoverable from a valid backup. Machine-specific keys and external services need separate secure recovery procedures. Backup integrity and restore drills are required before making recovery claims. See [`RESILIENCE_AND_RECOVERY.md`](RESILIENCE_AND_RECOVERY.md) and [`RISK_REGISTER.md`](../RISK_REGISTER.md).
