# Voice Interaction Target

Status: planned target. No wake word, speech recognition, speech synthesis, or voice control is implemented.

AgentGraph OS should support user-selectable wake-word and push-to-talk modes from the main PC, browser/PWA, and smartphone. The architecture preserves a local-first ASR/TTS path; a concrete engine is intentionally deferred until technical evaluation. Voice input carries the same structured identity, task, authorization, and approval boundaries as text input.

Voice is a conversational interface. It can surface concise status, approvals, and notifications under low bandwidth. It must not weaken authentication, turn speech into implicit authorization, or make Remote View/control available by default. The desired Lexi voice characteristics are natural, expressive, and conversational, but are not a vendor or engine decision. See [`LEXI.md`](LEXI.md) and [`REMOTE_INTERFACES.md`](REMOTE_INTERFACES.md).
