# Vision Rules

1. Route vision through project-owned multimodal model contracts; never hard-code a VLM in UI, domain, or graph runtime.
2. Vision is observation only. Do not add clicking, typing, browser control, or desktop automation.
3. Validate decoded image formats, byte size, dimensions, and allowlisted MIME types before storage or provider calls.
4. Store assets under generated locators; never use user filenames as paths or persist image base64 in the database/events/logs.
5. Folder access is fail-closed: canonical paths must stay under configured roots and may not traverse symlinks.
6. Use `read` for viewing, `execute` for uploads/analysis, and `control` for deleting/registering/scanning folders.
7. Tests must mock providers and use isolated storage. Do not download model weights in CI.
