# Phase 5 — Multimodal Vision Layer

## Mission

Extend AgentGraph OS with a secure, local-first multimodal vision layer.

The first supported local vision model is:

```text
LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

running through the existing local Ollama installation.

The goal is NOT to hard-code AgentGraph OS around one Liquid AI model.

The goal is to introduce a reusable multimodal architecture so AgentGraph OS can support:

- image understanding;
- image captioning;
- OCR;
- document analysis;
- object detection;
- grounding / bounding boxes;
- screen and UI understanding;
- batch image processing;
- controlled local-folder access;
- future vision-capable models and providers.

LFM2.5-VL-3B is only the first production vision model using this architecture.

---

# 1. Current Project Assumptions

Before changing code:

1. Read root `AGENTS.md`.
2. Read all linked agent rules relevant to:
   - architecture;
   - providers;
   - security;
   - remote interfaces;
   - frontend;
   - API;
   - database;
   - testing.
3. Read:
   - `docs/ARCHITECTURE.md`;
   - `docs/ROADMAP.md`;
   - `docs/PROJECT_STATUS.md`;
   - provider architecture documentation;
   - remote interface documentation;
   - current API documentation.
4. Inspect the actual repository before creating files.
5. Reuse existing project conventions rather than inventing parallel infrastructure.

Expected existing concepts include:

- FastAPI backend;
- `/api/v1`;
- SQLAlchemy persistence;
- Alembic migrations;
- ProviderRegistry;
- ModelRouter;
- Ollama provider;
- OpenCode provider;
- OpenAI-compatible provider;
- typed DTOs;
- Zod-validated frontend API;
- WebSocket event stream;
- remote authorization;
- React/Vite/TypeScript frontend;
- React Flow graph editor.

Verify these assumptions against the actual code.

If implementation names differ, preserve the actual architecture.

Do not rewrite functioning subsystems merely to match this document.

---

# 2. Phase Relationship

Phase 4 visual-interface manual acceptance may still be tracked independently.

Do not falsely mark Phase 4 as complete.

Do not silently modify existing Phase 4 acceptance records.

Phase 5 must preserve all Phase 4 functionality.

At the end, report the exact state of both phases separately.

---

# 3. Non-Negotiable Architecture Rule

Do NOT implement:

```text
UI
 ↓
LFM2.5-specific code
 ↓
Ollama
```

Implement:

```text
UI
 ↓
Vision API
 ↓
Vision Service
 ↓
ModelRouter / ProviderRegistry
 ↓
Multimodal Provider Contract
 ↓
Ollama Adapter
 ↓
LFM2.5-VL-3B
```

The model must be replaceable without rewriting the Vision UI or Vision API.

Future models may include other Ollama VLMs, OpenAI-compatible vision models, or other local runtimes.

---

# 4. Local Model

Default development vision model:

```text
hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

Default local Ollama API:

```text
http://127.0.0.1:11434
```

Do not download model weights into the Git repository.

Do not commit GGUF files.

Do not commit Hugging Face caches.

Do not bundle model weights into frontend or backend packages.

Model installation is an external runtime prerequisite.

---

# 5. Configuration

Add explicit vision configuration using the existing project settings system.

Required concepts:

```text
AGENTGRAPH_VISION_ENABLED
AGENTGRAPH_VISION_PROVIDER
AGENTGRAPH_VISION_MODEL
AGENTGRAPH_VISION_ALLOWED_ROOTS
AGENTGRAPH_VISION_STORAGE_ROOT
```

Default model:

```text
hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

Default provider:

```text
ollama
```

Security defaults:

```text
VISION_ENABLED=false
ALLOWED_ROOTS=[]
```

Vision filesystem access must fail closed.

Do not expose arbitrary host filesystem access by default.

Document all variables in `.env.example`.

Never place secrets or user-specific absolute paths in `.env.example`.

---

# 6. Multimodal Provider Contract

Extend the existing model/provider abstractions.

Do not create a completely separate LLM stack.

Introduce typed multimodal request parts conceptually equivalent to:

```text
TextPart
ImagePart
```

For example:

```python
TextPart(
    type="text",
    text="Describe this image."
)

ImagePart(
    type="image",
    data=...,
    mime_type="image/jpeg"
)
```

Exact names must follow existing project conventions.

Provider/model metadata must expose capabilities.

Minimum capability set:

```text
text
vision
image_captioning
ocr
grounding
ui_understanding
multi_image
function_calling
```

Capabilities must be discoverable from the provider/model API.

Text-only calls must continue working unchanged.

Existing provider tests must continue passing.

---

# 7. Ollama Multimodal Support

Extend the existing Ollama adapter.

Do not introduce a second Ollama client unless technically necessary.

Support vision messages through Ollama's image-capable API.

Image payloads must be converted only at the provider boundary.

Internal services should operate on typed image references/bytes rather than raw provider-specific JSON.

Do not persist base64 copies of images in database records.

Do not publish base64 image data over WebSocket events.

The adapter must support:

```text
text-only request
single image + text
multiple images + text
```

Return the normal normalized provider response used by AgentGraph OS.

Record:

```text
provider
model
latency
usage metadata when available
error metadata
```

without recording raw image contents.

---

# 8. Vision Domain

Introduce a proper vision domain/service layer.

Suggested concepts:

```text
VisionAsset
VisionAnalysis
VisionFolder
VisionMode
VisionResult
```

Adapt naming to current project conventions.

---

# 9. VisionAsset

A VisionAsset represents an image known to AgentGraph OS.

Store metadata such as:

```text
id
filename
mime_type
size_bytes
sha256
source_type
storage_locator
created_at
```

Do not expose sensitive host filesystem paths unnecessarily through remote APIs.

Never use a user-supplied filename directly as a filesystem path.

Use generated storage identifiers.

---

# 10. VisionAnalysis

A VisionAnalysis represents one model execution against an asset.

Store:

```text
id
asset_id
run_id when applicable
provider
model
mode
prompt
status
raw_text
description
ocr_text
structured_result
latency_ms
error_code
created_at
completed_at
```

Use appropriate JSON/database types according to existing database conventions.

Analyses must survive application restart.

Create an Alembic migration.

Migration must work:

```text
upgrade
downgrade
fresh database
existing database
```

---

# 11. Supported Vision Modes

Implement these initial modes:

## describe

General factual image description.

Prompt intent:

```text
Describe what is visible in the image.
Be factual.
Do not invent details that cannot be determined from the image.
```

---

## detailed

More detailed visual description.

Include:

- scene;
- people;
- visible objects;
- activities;
- spatial relationships;
- relevant visual details.

Do not infer identity, private information, intent, or invisible facts.

---

## ocr

Extract visible text.

Preserve useful layout where possible.

Store:

```text
raw OCR output
normalized OCR text
layout information when available
```

---

## objects

Identify visually detectable objects.

Prefer structured results where reliable.

---

## grounding

Locate an object or UI element described by the user.

Normalize bounding boxes.

Define one internal coordinate representation and document it.

Do not let provider-specific coordinate formats leak into the frontend.

---

## ui

Analyze screenshots and interfaces.

Return useful fields such as:

```text
screen description
visible controls
visible text
candidate interactive elements
bounding boxes when available
```

This phase must NOT automatically click, type, or control the computer.

Vision is observation only.

Computer control belongs to a later explicitly authorized phase.

---

## custom

User-supplied prompt plus image.

Apply normal authorization and input limits.

---

# 12. Upload API

Create versioned endpoints under:

```text
/api/v1/vision
```

Exact route structure may be adapted to existing API conventions.

Required operations:

```text
POST /api/v1/vision/assets
GET  /api/v1/vision/assets
GET  /api/v1/vision/assets/{id}
DELETE /api/v1/vision/assets/{id}
```

Upload endpoint must support multipart image upload.

Supported image formats must be explicit and allowlisted.

At minimum consider:

```text
JPEG
PNG
WEBP
```

Only add formats that the actual processing stack supports reliably.

Validate:

- MIME type;
- decoded image format;
- configured file-size limit;
- image dimensions;
- corrupted images.

Do not trust filename extensions.

---

# 13. Analysis API

Required operation concept:

```text
POST /api/v1/vision/assets/{id}/analyses
```

Request:

```json
{
  "mode": "describe",
  "prompt": null,
  "model": null
}
```

If model is omitted, use the configured/default vision-capable model.

Reject a model that lacks the required capability.

Return an analysis identifier immediately if processing is asynchronous.

Do not block long batch requests in one HTTP transaction.

---

# 14. Folder Access

Add controlled local-folder support.

A browser or remote client must NEVER be able to submit an arbitrary path and browse the host filesystem.

Implement explicit registered folders.

Conceptually:

```text
VisionFolder
```

Fields:

```text
id
display_name
root
enabled
watch_enabled
created_at
```

A folder must resolve underneath one of:

```text
AGENTGRAPH_VISION_ALLOWED_ROOTS
```

Resolve canonical filesystem paths before access.

Reject:

```text
..
symlink escapes
path traversal
paths outside allowed roots
special files
sockets
devices
```

Do not recursively follow symlinks outside the registered root.

---

# 15. Folder APIs

Implement appropriately authorized operations equivalent to:

```text
GET  /api/v1/vision/folders
POST /api/v1/vision/folders
DELETE /api/v1/vision/folders/{id}
POST /api/v1/vision/folders/{id}/scan
```

Folder registration is a privileged control operation.

Normal read-only remote users must not gain permission to register arbitrary folders.

---

# 16. Folder Scan

Scanning a registered folder must:

1. enumerate supported image files;
2. canonicalize paths;
3. deduplicate using stable metadata/hash rules;
4. create/update VisionAssets;
5. optionally enqueue analyses;
6. expose progress;
7. survive individual-file failures;
8. produce a final summary.

One corrupt image must not fail the entire batch.

Return counts:

```text
discovered
accepted
skipped
processed
failed
```

---

# 17. Optional Watch Mode

Implement watch mode only if it can be done reliably with bounded resource usage.

When enabled for a registered folder:

```text
new supported image
        ↓
filesystem event
        ↓
debounce / validation
        ↓
VisionAsset
        ↓
optional automatic analysis
```

Requirements:

- no busy polling;
- bounded queue;
- duplicate-event suppression;
- clean shutdown;
- explicit enable/disable;
- errors visible to user.

If a reliable watch implementation would destabilize the phase, finish deterministic folder scanning first and record watch mode as deferred rather than implementing a fragile watcher.

---

# 18. Vision Job Queue

Image processing must not freeze the API or frontend.

Use the existing execution/runtime architecture where possible.

Do not introduce Redis/Celery or another infrastructure dependency unless the repository already uses it or there is a proven requirement.

Use a bounded concurrency policy.

CPU-only machines are first-class targets.

Default concurrency for expensive local vision processing must be conservative.

Expose queue state.

Support cancellation if it naturally fits the existing run cancellation infrastructure.

---

# 19. Events

Publish normalized events through the existing remote event system.

Examples:

```text
vision.asset.created
vision.analysis.queued
vision.analysis.started
vision.analysis.completed
vision.analysis.failed

vision.folder.scan.started
vision.folder.scan.progress
vision.folder.scan.completed
vision.folder.scan.failed
```

Events must contain metadata only.

Never send:

```text
raw image bytes
base64 images
model secrets
unfiltered host paths
```

Reuse the existing event redaction mechanism.

---

# 20. Authorization

Integrate with the existing principal/permission system.

Introduce the minimum necessary permissions consistent with existing naming conventions.

Conceptually:

```text
vision.read
vision.analyze
vision.manage
vision.folder.read
vision.folder.manage
```

Avoid permission proliferation if existing `read`, `execute`, and `control` permissions can safely represent these operations.

Document the final mapping.

Important:

- viewing analysis results is read-like;
- starting analysis is execute-like;
- registering host folders is control-like;
- deleting assets/folders is control-like.

Remote authorization remains disabled unless explicitly enabled by existing project policy.

---

# 21. Security

This section is blocking.

Prevent:

## Path traversal

```text
../../.ssh
```

must fail.

## Symlink escape

A symlink inside an allowed directory pointing outside it must not bypass policy.

## Oversized files

Reject files exceeding configured limits before expensive model processing.

## Unsupported content

Do not feed arbitrary executables or unvalidated binary content to the vision runtime.

## Filename attacks

Never trust original names for storage paths.

## Remote filesystem enumeration

Never expose unrestricted host directory browsing.

## Event leakage

Do not publish raw image contents.

## Log leakage

Do not log base64 images.

## Repository pollution

Downloaded/uploaded images and GGUF files must never appear as untracked project assets during normal use.

Update `.gitignore` where appropriate.

---

# 22. Frontend — Vision Workspace

Add a first-class navigation entry:

```text
Vision
```

Follow the existing Phase 4 visual language.

Do not create a visually unrelated mini-application.

The page must be usable on:

```text
desktop
tablet
mobile browser
```

---

# 23. Vision Workspace Layout

Provide three primary flows:

```text
Upload
Folders
History
```

---

# 24. Upload Flow

Support:

- click to choose files;
- drag and drop;
- multiple images;
- preview;
- removal before processing;
- mode selector;
- custom prompt;
- model selector when multiple compatible models exist;
- Analyze action.

Show:

```text
filename
dimensions
size
status
```

---

# 25. Analysis Result

For each asset show:

```text
image preview
description
OCR
objects
grounding/UI result when applicable
model
provider
processing status
latency
timestamp
```

Use tabs/panels where appropriate:

```text
Description
OCR
Objects
UI
Raw
```

Do not expose developer-only payloads by default.

Raw output may be available in an advanced/details view.

---

# 26. Batch UX

For folder or multi-image processing show:

```text
processed / total
queued
running
completed
failed
```

Each image must have its own status.

One failed image must not hide successful results.

Allow retry for failed analyses.

---

# 27. Folder UI

The Folders section must show only registered folders.

Example:

```text
Screenshots
/home/.../Pictures/Screenshots
34 images
Last scan: ...
[Scan]
```

Do not expose arbitrary filesystem browser functionality through the remote web UI.

Folder creation/registration controls must respect authorization.

---

# 28. History

Persist and display previous analyses.

Allow useful filters:

```text
model
mode
status
date
filename
```

Basic textual search over descriptions/OCR may be added if it can be implemented without introducing a new search engine.

Do NOT implement vector search in this phase.

Vector visual search belongs to a later phase.

---

# 29. Model Discovery

Update provider/model discovery so the frontend can distinguish:

```text
text-only model
vision-capable model
OCR-capable model
grounding-capable model
```

The Vision Workspace must not offer incompatible models.

The existing normal model selector must continue to work.

---

# 30. Graph Integration

Introduce a reusable graph capability for vision.

Add a node equivalent to:

```text
Vision Analyze
```

Inputs:

```text
image / asset reference
mode
optional prompt
optional model reference
```

Outputs:

```text
description
ocr_text
structured_result
asset_id
analysis_id
```

Do not hard-code LFM2.5 into node execution.

The node must route through ModelRouter/ProviderRegistry.

---

# 31. Example Graph

The following graph must be possible:

```text
Image Asset
    ↓
Vision Analyze
    ↓
Text Agent
    ↓
Final Output
```

And:

```text
Folder Scan
    ↓
Vision Analyze
    ↓
Result
```

Do not implement autonomous GUI clicking in this phase.

---

# 32. Provider Error Normalization

Normalize expected errors:

```text
vision_model_unavailable
vision_model_not_found
vision_capability_missing
vision_invalid_image
vision_image_too_large
vision_folder_forbidden
vision_analysis_failed
vision_timeout
```

Map provider-specific Ollama errors into AgentGraph errors.

Frontend must display actionable messages.

---

# 33. Ollama Health

Expose enough state to distinguish:

```text
Ollama unavailable
model not installed
model installed
vision capability available
```

Do not auto-download multi-gigabyte models silently during normal API calls.

If the configured model is not installed, return a clear error/instruction.

Model installation must be explicit.

---

# 34. Default Model

The application may suggest/configure:

```text
hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

but must not change the existing normal text default model.

The existing:

```text
auto://default
```

text-routing behavior must remain compatible.

Vision routing and text routing must remain distinct when necessary.

---

# 35. Database Migration

Create an Alembic migration for all new persisted entities.

Verify:

```bash
uv run --directory backend alembic upgrade head
```

Also verify a clean database can migrate from zero to head.

If project tests include migration checks, extend them.

---

# 36. Backend Tests

Add automated tests for:

## Provider

- text-only Ollama remains functional;
- one-image payload;
- multi-image payload;
- vision capability discovery;
- malformed provider response;
- timeout;
- unavailable Ollama;
- unavailable model.

## Vision service

- create asset;
- analyze asset;
- description result;
- OCR result;
- invalid file;
- unsupported MIME;
- duplicate asset;
- persisted analysis.

## Filesystem security

- allowed root;
- forbidden root;
- `..` traversal;
- symlink escape;
- deleted file;
- unreadable file.

## Batch

- multiple files;
- corrupt file among valid files;
- bounded concurrency;
- partial failure;
- progress events.

## Authorization

- read;
- execute/analyze;
- folder management;
- denied operations.

Use mocks for normal CI.

CI must not download LFM2.5-VL-3B.

---

# 37. Frontend Tests

Cover:

- Vision route renders;
- upload interaction;
- model capability filtering;
- analysis lifecycle;
- completed result;
- provider error;
- batch progress;
- failed batch item;
- folder permission denial;
- mobile/responsive behavior where existing test tooling allows it.

---

# 38. Live Smoke Test

Automated CI must not require the real model.

Add a separate documented live smoke procedure.

Prerequisite:

```bash
ollama run hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

Live smoke must use a known local test image.

Verify:

1. Ollama sees the model.
2. AgentGraph provider discovery sees the model.
3. Vision capability is reported.
4. Upload image.
5. Run `describe`.
6. Receive non-empty description.
7. Run OCR against a text-containing fixture.
8. Receive non-empty OCR output.
9. Persist results.
10. Reload browser.
11. Results remain available.

Do not use exact generated wording as a brittle assertion.

---

# 39. Performance Measurement

Record live local measurements without fabricating expected performance.

For each live smoke record:

```text
CPU
RAM
model
quantization
image dimensions
analysis mode
time to completion
peak memory if available
```

Do not claim Liquid AI benchmark speeds for the developer machine.

Create documentation for repeatable local benchmarking.

---

# 40. Manual Acceptance

Manual acceptance is mandatory.

## Single image

- open Vision;
- upload JPG;
- preview is correct;
- select Description;
- analyze;
- result appears;
- refresh page;
- result remains.

## PNG screenshot

- upload screenshot;
- run OCR;
- visible text is extracted;
- run UI mode;
- interface description appears.

## Folder

- configure one allowed root;
- register one folder under it;
- scan folder;
- images appear;
- batch analysis runs;
- progress updates live;
- individual results can be opened.

## Security

Attempt to register:

```text
/etc
~/.ssh
..
```

or another path outside configured roots.

It must fail.

Test symlink escape.

It must fail.

## Failure state

Stop Ollama and run an analysis.

UI must show a normalized provider-unavailable error rather than hang.

Restart Ollama and retry successfully.

---

# 41. No Computer Control Yet

Phase 5 is perception.

It is NOT autonomous computer use.

Do not add:

```text
mouse control
keyboard injection
automatic clicking
automatic browser navigation
desktop automation
screen-control loop
```

The UI/grounding data must be designed so a future phase can consume it safely.

A future phase may implement:

```text
observe
→ understand
→ plan
→ authorize
→ act
→ observe
```

but that is explicitly outside Phase 5.

---

# 42. Documentation

Update at minimum:

```text
docs/ARCHITECTURE.md
docs/ROADMAP.md
docs/PROJECT_STATUS.md
.env.example
AGENTS.md
```

when appropriate under current repository rules.

Create focused documentation such as:

```text
docs/architecture/VISION.md
docs/agent-rules/VISION.md
docs/VISION_LOCAL_SETUP.md
docs/PHASE_5_MANUAL_ACCEPTANCE.md
```

Use actual documentation naming conventions if they differ.

---

# 43. VISION.md Architecture Document

Document:

```text
VisionAsset
VisionAnalysis
VisionFolder
provider capability model
multimodal request flow
Ollama flow
filesystem security boundary
upload storage
event lifecycle
graph-node integration
future extension points
```

Include a diagram similar to:

```text
Browser
   ↓
/api/v1/vision
   ↓
Vision Service
   ↓
ModelRouter
   ↓
ProviderRegistry
   ↓
OllamaProvider
   ↓
Ollama :11434
   ↓
LFM2.5-VL-3B
```

---

# 44. Agent Rules

Create concise rules telling future OpenCode sessions:

- never hard-code one VLM into domain logic;
- never expose arbitrary host filesystem access;
- never commit models;
- never log image bytes/base64;
- use capability-based routing;
- preserve local-first behavior;
- keep vision observation separate from computer-control actions;
- add provider implementations behind interfaces;
- require authorization for folder management.

Link these rules from `AGENTS.md` without bloating root context.

---

# 45. Dependency Policy

Prefer existing project dependencies.

Do not add large dependencies merely to manipulate basic image metadata.

Any new dependency must have a clear reason.

Do not introduce:

```text
Celery
Redis
Kafka
external object storage
vector database
```

solely for this phase unless already present and justified by the actual architecture.

---

# 46. Backward Compatibility

Phase 5 must not break:

- existing projects;
- agents;
- graph persistence;
- graph execution;
- text LLM routing;
- Ollama text models;
- OpenCode provider;
- OpenAI-compatible provider;
- runs;
- approvals;
- remote event stream;
- settings;
- existing Phase 4 UI routes.

Existing API clients must continue functioning.

---

# 47. Required Quality Gates

Run the project's actual required checks.

At minimum, where applicable:

```text
ruff
mypy
pytest
pnpm check
frontend tests
build
Alembic migration validation
```

Do not report PASS without executing the command.

If a check cannot run, report:

```text
NOT RUN
```

with the exact reason.

Do not convert NOT RUN into PASS.

---

# 48. Completion Criteria

Phase 5 is DONE only when all of the following are true:

- multimodal provider abstraction exists;
- Ollama adapter supports images;
- LFM2.5-VL-3B works as a local vision model;
- provider discovery exposes vision capabilities;
- image upload exists;
- persisted VisionAsset exists;
- persisted VisionAnalysis exists;
- Description mode works;
- OCR mode works;
- Objects mode works;
- UI mode works;
- Grounding architecture works;
- registered folder access exists;
- folder security is enforced;
- batch processing exists;
- progress events exist;
- Vision Workspace exists;
- history exists;
- Vision graph node exists;
- backend tests pass;
- frontend checks pass;
- migrations pass;
- live LFM smoke has been performed or explicitly remains NOT RUN;
- manual browser acceptance is recorded;
- documentation is updated.

If manual acceptance has not been performed:

```text
Status: IN REVIEW
```

not DONE.

If the real LFM model has not been tested:

```text
Live LFM smoke: NOT RUN
```

not PASS.

---

# 49. Final Completion Report

At the end return a structured report:

```text
Phase 5 — Multimodal Vision Layer

Status:
PASS / PARTIAL / IN REVIEW / FAIL

Implemented:
- ...

Architecture:
- ...

Files created:
- ...

Files modified:
- ...

Database migrations:
- ...

API changes:
- ...

Provider changes:
- ...

Frontend changes:
- ...

Security controls:
- ...

Tests:
- Ruff:
- mypy:
- pytest:
- frontend:
- build:
- migrations:

Live LFM2.5-VL-3B smoke:
- model:
- quantization:
- device:
- image:
- result:
- latency:
- status:

Manual acceptance:
- ...

Known limitations:
- ...

Deferred:
- ...

Phase 4 status:
- ...

Phase 5 status:
- ...

Recommended next phase:
- ...
```

Do not claim anything that was not actually executed.

---

# 50. Expected Future Direction

Do not implement this now, but leave clean extension points for a later phase:

```text
Phase 6 — Visual Computer Agent
```

Potential future architecture:

```text
Screen Capture
      ↓
Vision Provider
      ↓
UI Grounding
      ↓
Agent Planning
      ↓
Authorization / Approval
      ↓
Computer Action
      ↓
New Screen Capture
```

Phase 5 must provide the safe perception foundation for that future work.

---

# Official Model References

Use these as upstream technical references:

```text
https://huggingface.co/LiquidAI/LFM2.5-VL-3B
https://huggingface.co/LiquidAI/LFM2.5-VL-3B-GGUF
https://www.liquid.ai/blog/lfm2-5-vl-3b
https://docs.liquid.ai/deployment/on-device/llama-cpp
https://docs.ollama.com/capabilities/vision
```

Do not rely on unofficial model forks when an official LiquidAI checkpoint exists.

---

# Final Instruction

Implement Phase 5 end-to-end.

First inspect the existing repository and produce a short implementation map based on the real codebase.

Then implement the phase incrementally.

Preserve existing architecture and tests.

Do not stop after scaffolding.

Do not replace working systems with parallel implementations.

Do not silently weaken security.

Do not mark manual or live checks as complete unless they were actually performed.

The final result should make AgentGraph OS capable of securely receiving local images, analyzing them through a replaceable local multimodal provider, processing registered image folders, persisting results, exposing them in the browser, and using vision as a first-class graph capability.