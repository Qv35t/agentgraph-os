# Phase 5 — Multimodal Vision Layer

## Mission

Add secure, local-first multimodal image observation through existing model and
remote-interface boundaries without coupling the application to one VLM.

## Required scope direction

- typed multimodal model parts through ModelRouter/provider contracts;
- Ollama image adapter and discoverable vision capability;
- validated local asset storage and persisted analysis records;
- fail-closed registered folders and metadata-only events;
- versioned vision API and browser Vision workspace;
- deterministic mocked tests without downloading local models.

## Security/privacy

Images remain local by default. Do not expose arbitrary host paths, image bytes,
base64 data, model credentials, or computer-control actions.

## Gate

Users can upload approved image types, run a configured local vision model through
the provider boundary, reload persisted results, and scan only registered folders
under allowed roots. Live model and manual browser acceptance remain separate
required gates.

Refine exact storage/schema choices from the implemented Phase 4/runtime state before coding.
