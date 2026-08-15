# Local Vision Setup

Vision is disabled by default. Install the model explicitly outside the
repository:

```bash
ollama run hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
```

Use a user-owned environment file to enable it. Do not commit paths, models, or
credentials:

```text
AGENTGRAPH_VISION_ENABLED=true
AGENTGRAPH_VISION_PROVIDER=ollama
AGENTGRAPH_VISION_MODEL=hf.co/LiquidAI/LFM2.5-VL-3B-GGUF:Q4_K_M
AGENTGRAPH_VISION_ALLOWED_ROOTS=["/absolute/path/you/control"]
```

Use the Vision workspace to upload an image and run `describe` or `ocr`. Folder
registration is available only under configured allowed roots and requires the
existing `control` permission.
