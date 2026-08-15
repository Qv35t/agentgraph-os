# Multimodal Vision Layer

```mermaid
flowchart LR
  UI[Vision workspace] --> API[/api/v1/vision]
  API --> Service[VisionService]
  Service --> Store[Generated local asset storage]
  Service --> Router[ModelRouter]
  Router --> Ollama[OllamaProvider]
  Ollama --> Model[Configured local vision model]
  Service --> Events[Normalized runtime events]
```

`VisionService` is a local-first application service. It validates JPEG, PNG,
and WEBP payloads using decoded Pillow format and configured byte/pixel limits.
Assets use SHA-256 generated storage locators; remote APIs expose metadata only.
`VisionAnalysis` records normalized text, provider/model metadata, latency, and
errors without storing source image bytes/base64.

Vision provider calls use `ImagePart` inside the existing `ModelMessage` and
`ModelRouter` contract. Ollama encodes images only at its adapter boundary. The
configured model defaults to `hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M`, but the
architecture remains provider/model-reference based.

Registered folders are privileged. Their resolved paths must fall under
`AGENTGRAPH_VISION_ALLOWED_ROOTS`; unregistered paths, path traversal, and
symlink entries are rejected. Folder roots are not returned by remote APIs.

The Vision workspace supports upload, analysis history, and registered-folder
scans. The persisted `vision-analyze` graph node is configuration metadata for
future graph execution; it does not introduce computer-control behavior.

Watch mode, batch auto-analysis, durable queue recovery, and model-specific
grounding normalization remain deferred. Analyses run through a process-local,
single-concurrency background queue and persist their terminal status.
