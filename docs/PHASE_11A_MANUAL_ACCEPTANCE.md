# Phase 11A Manual Acceptance

Status: NOT RUN.

1. Upgrade an isolated Phase 10 database and start the backend/frontend.
2. Read the owner-only bootstrap secret from the configured local security
   directory, bootstrap the first owner, and confirm it cannot be reused.
3. Register a localhost passkey, log out, and authenticate with that passkey.
4. Enroll TOTP, confirm the first code, then confirm an incorrect code fails.
5. Refresh and restart the backend; confirm the session, device, approvals, and
   lockdown state follow their durable policy.
6. Create a controlled approval, restart before deciding, and confirm no run is
   resumed or replayed.
7. Create and revoke a scoped grant; verify mismatched scope is denied.
8. Add a test vault credential and verify metadata APIs never return its value.
9. Activate lockdown, verify privileged actions are denied and grants revoked,
   then deactivate it from a strong local owner session.
10. Confirm the audit view has relevant security events and no secret values.
