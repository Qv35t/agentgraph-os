# Phase 5 Manual Acceptance

## Prerequisites

- Complete Phase 4 remains verified.
- The configured local Ollama vision model is installed explicitly.
- Vision is enabled through a user-owned environment file with at least one
  allowed root.

## Required checks

- Upload a JPEG/PNG/WEBP, run `describe`, refresh, and confirm the persisted result.
- Upload a screenshot, run `ocr` and `ui`, and inspect non-empty model output.
- Register a folder under an allowed root, scan it, and confirm metadata-only
  assets/history appear.
- Attempt `/etc`, `..`, and a symlink escape; each must be rejected.
- Stop Ollama, submit analysis, and confirm normalized failure; restart and retry.
- Verify desktop/tablet/mobile Vision workspace controls.

## Completion

Automated mocks, migration verification, local model smoke, and browser manual
acceptance were owner-confirmed complete on 2026-08-15.
