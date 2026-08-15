import asyncio
import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from agentgraph.domain.remote import RuntimeEvent, RuntimeEventType
from agentgraph.domain.vision import VisionAnalysisStatus, VisionMode
from agentgraph.models.contracts import ImagePart, ModelMessage, ModelRouterError
from agentgraph.models.router import ModelRouter
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import VisionAnalysisRecord, VisionAssetRecord, VisionFolderRecord
from agentgraph.runtime.events import RuntimeEventBus
from agentgraph.settings import Settings

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class VisionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class VisionService:
    def __init__(
        self, session_factory: SessionFactory, router: ModelRouter, events: RuntimeEventBus, settings: Settings
    ) -> None:
        self._session_factory = session_factory
        self._router = router
        self._events = events
        self._settings = settings
        self._storage_root = Path(settings.vision_storage_root).resolve()
        self._allowed_roots = _allowed_roots(settings.vision_allowed_roots)
        self._tasks: dict[asyncio.Task[None], str] = {}
        self._semaphore = asyncio.Semaphore(1)

    async def create_asset(
        self, filename: str, declared_mime: str | None, data: bytes, source_type: str = "upload"
    ) -> VisionAssetRecord:
        self._require_enabled()
        if len(data) > self._settings.vision_max_file_size_bytes:
            raise VisionError("vision_image_too_large", "Image exceeds the configured size limit")
        image_format, mime_type = _validate_image(data, self._settings.vision_max_image_pixels)
        if declared_mime and declared_mime != mime_type:
            raise VisionError("vision_invalid_image", "Declared MIME type does not match decoded image")
        digest = hashlib.sha256(data).hexdigest()
        locator = f"{digest}.{image_format.lower()}"
        async with self._session_factory() as session:
            existing = await session.scalar(select(VisionAssetRecord).where(VisionAssetRecord.sha256 == digest))
            if existing is not None:
                return existing
            self._storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            await asyncio.to_thread(_write_private, self._storage_root / locator, data)
            asset = VisionAssetRecord(
                filename=_safe_filename(filename),
                mime_type=mime_type,
                size_bytes=len(data),
                sha256=digest,
                source_type=source_type,
                storage_locator=locator,
            )
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
        await self._publish(
            RuntimeEventType.VISION_ASSET_CREATED,
            {"asset_id": asset.id, "mime_type": asset.mime_type, "size_bytes": asset.size_bytes},
        )
        return asset

    async def list_assets(self) -> list[VisionAssetRecord]:
        self._require_enabled()
        async with self._session_factory() as session:
            return list(await session.scalars(select(VisionAssetRecord).order_by(VisionAssetRecord.created_at.desc())))

    async def get_asset(self, asset_id: UUID) -> VisionAssetRecord:
        self._require_enabled()
        async with self._session_factory() as session:
            asset = await session.get(VisionAssetRecord, str(asset_id))
            if asset is None:
                raise VisionError("vision_asset_not_found", "Vision asset was not found")
            return asset

    async def delete_asset(self, asset_id: UUID) -> None:
        asset = await self.get_asset(asset_id)
        async with self._session_factory() as session:
            record = await session.get(VisionAssetRecord, asset.id)
            if record is not None:
                await session.delete(record)
                await session.commit()
        path = self._storage_root / asset.storage_locator
        if path.exists():
            await asyncio.to_thread(path.unlink)

    async def submit_analysis(
        self, asset_id: UUID, mode: VisionMode, prompt: str | None, model: str | None
    ) -> VisionAnalysisRecord:
        asset = await self.get_asset(asset_id)
        model_ref = model or f"{self._settings.vision_provider}://{self._settings.vision_model}"
        provider, _, model_id = model_ref.partition("://")
        if provider != self._settings.vision_provider or model_id != self._settings.vision_model:
            raise VisionError(
                "vision_capability_missing", "Selected vision model is not available through the configured provider"
            )
        if len(self._tasks) >= self._settings.vision_max_queue:
            raise VisionError("vision_queue_full", "Vision queue is at its configured limit")
        analysis = VisionAnalysisRecord(
            asset_id=asset.id,
            provider_id=provider,
            model_id=model_id,
            mode=mode,
            prompt=prompt,
            status=VisionAnalysisStatus.QUEUED,
        )
        async with self._session_factory() as session:
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)
        await self._publish(
            RuntimeEventType.VISION_ANALYSIS_QUEUED, {"analysis_id": analysis.id, "asset_id": asset.id, "mode": mode}
        )
        task = asyncio.create_task(self._execute_analysis(analysis.id), name=f"vision-analysis-{analysis.id}")
        self._tasks[task] = analysis.id
        task.add_done_callback(self._tasks.pop)
        return analysis

    async def get_analysis(self, analysis_id: UUID) -> VisionAnalysisRecord:
        self._require_enabled()
        async with self._session_factory() as session:
            analysis = await session.get(VisionAnalysisRecord, str(analysis_id))
            if analysis is None:
                raise VisionError("vision_analysis_not_found", "Vision analysis was not found")
            return analysis

    async def list_analyses(self) -> list[VisionAnalysisRecord]:
        self._require_enabled()
        async with self._session_factory() as session:
            return list(
                await session.scalars(select(VisionAnalysisRecord).order_by(VisionAnalysisRecord.created_at.desc()))
            )

    async def register_folder(self, display_name: str, root: str) -> VisionFolderRecord:
        self._require_enabled()
        path = _allowed_directory(Path(root), self._allowed_roots)
        async with self._session_factory() as session:
            record = VisionFolderRecord(display_name=display_name, root=str(path))
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def list_folders(self) -> list[VisionFolderRecord]:
        self._require_enabled()
        async with self._session_factory() as session:
            return list(await session.scalars(select(VisionFolderRecord).order_by(VisionFolderRecord.created_at)))

    async def scan_folder(self, folder_id: UUID) -> dict[str, int]:
        self._require_enabled()
        async with self._session_factory() as session:
            folder = await session.get(VisionFolderRecord, str(folder_id))
            if folder is None:
                raise VisionError("vision_folder_not_found", "Vision folder was not found")
        root = _allowed_directory(Path(folder.root), self._allowed_roots)
        counts = {"discovered": 0, "accepted": 0, "skipped": 0, "failed": 0}
        await self._publish(RuntimeEventType.VISION_FOLDER_SCAN_STARTED, {"folder_id": folder.id})
        for path in root.rglob("*"):
            if counts["discovered"] >= self._settings.vision_max_scan_files:
                counts["skipped"] += 1
                break
            if not path.is_file() or path.is_symlink():
                continue
            counts["discovered"] += 1
            try:
                data = await asyncio.to_thread(_read_regular_file, path, self._settings.vision_max_file_size_bytes)
                await self.create_asset(path.name, None, data, source_type="folder")
                counts["accepted"] += 1
            except VisionError:
                counts["skipped"] += 1
            except OSError:
                counts["failed"] += 1
        await self._publish(RuntimeEventType.VISION_FOLDER_SCAN_COMPLETED, {"folder_id": folder.id, **counts})
        return counts

    async def shutdown(self) -> None:
        pending = dict(self._tasks)
        for task in pending:
            task.cancel()
        if pending:
            _, still_running = await asyncio.wait(pending, timeout=self._settings.cancellation_timeout_seconds)
            for task, analysis_id in pending.items():
                if task in still_running or task.cancelled():
                    await self._mark_failed(analysis_id, "vision_cancelled")

    async def recover_stale_analyses(self) -> None:
        async with self._session_factory() as session:
            active = await session.scalars(
                select(VisionAnalysisRecord).where(
                    VisionAnalysisRecord.status.in_((VisionAnalysisStatus.QUEUED, VisionAnalysisStatus.RUNNING))
                )
            )
            for analysis in active:
                analysis.status = VisionAnalysisStatus.FAILED
                analysis.error_code = "vision_interrupted"
                analysis.completed_at = datetime.now(UTC)
            await session.commit()

    async def _execute_analysis(self, analysis_id: str) -> None:
        async with self._semaphore:
            async with self._session_factory() as session:
                analysis = await session.get(VisionAnalysisRecord, analysis_id)
                if analysis is None:
                    return
                asset = await session.get(VisionAssetRecord, analysis.asset_id)
                if asset is None:
                    return
                analysis.status = VisionAnalysisStatus.RUNNING
                await session.commit()
            await self._publish(
                RuntimeEventType.VISION_ANALYSIS_STARTED, {"analysis_id": analysis_id, "asset_id": asset.id}
            )
            try:
                data = await asyncio.to_thread((self._storage_root / asset.storage_locator).read_bytes)
                response = await self._router.complete(
                    f"{analysis.provider_id}://{analysis.model_id}",
                    [
                        ModelMessage(
                            role="user",
                            content=_prompt(analysis.mode, analysis.prompt),
                            images=(ImagePart(data, asset.mime_type),),
                        )
                    ],
                )
                async with self._session_factory() as session:
                    record = await session.get(VisionAnalysisRecord, analysis_id)
                    if record is None or record.status is not VisionAnalysisStatus.RUNNING:
                        return
                    record.status = VisionAnalysisStatus.COMPLETED
                    record.raw_text = response.content
                    record.description = response.content if record.mode is not VisionMode.OCR else None
                    record.ocr_text = response.content if record.mode is VisionMode.OCR else None
                    record.latency_ms = response.latency_ms
                    record.completed_at = datetime.now(UTC)
                    await session.commit()
                await self._publish(
                    RuntimeEventType.VISION_ANALYSIS_COMPLETED, {"analysis_id": analysis_id, "asset_id": asset.id}
                )
            except asyncio.CancelledError:
                await self._mark_failed(analysis_id, "vision_cancelled")
                raise
            except Exception as error:
                await self._mark_failed(
                    analysis_id, error.code if isinstance(error, ModelRouterError) else "vision_analysis_failed"
                )
                await self._publish(
                    RuntimeEventType.VISION_ANALYSIS_FAILED, {"analysis_id": analysis_id}, severity="error"
                )

    def _require_enabled(self) -> None:
        if not self._settings.vision_enabled:
            raise VisionError("vision_disabled", "Vision is disabled by server configuration")

    async def _publish(self, type: RuntimeEventType, payload: dict[str, object], severity: str = "info") -> None:
        await self._events.publish(
            RuntimeEvent.create(type, self._settings.project_id, payload=payload, severity=severity)
        )

    async def _mark_failed(self, analysis_id: str, error_code: str) -> None:
        async with self._session_factory() as session:
            record = await session.get(VisionAnalysisRecord, analysis_id)
            if record is not None and record.status in {VisionAnalysisStatus.QUEUED, VisionAnalysisStatus.RUNNING}:
                record.status = VisionAnalysisStatus.FAILED
                record.error_code = error_code
                record.completed_at = datetime.now(UTC)
                await session.commit()


def _validate_image(data: bytes, max_pixels: int) -> tuple[str, str]:
    try:
        with Image.open(BytesIO(data), formats=tuple(ALLOWED_FORMATS)) as image:
            image.verify()
        with Image.open(BytesIO(data), formats=tuple(ALLOWED_FORMATS)) as image:
            if image.width * image.height > max_pixels:
                raise VisionError("vision_image_too_large", "Image dimensions exceed the configured limit")
            image_format = image.format
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as error:
        raise VisionError("vision_invalid_image", "Uploaded content is not a supported image") from error
    if image_format not in ALLOWED_FORMATS:
        raise VisionError("vision_invalid_image", "Image format is not allowed")
    return image_format, ALLOWED_FORMATS[image_format]


def _allowed_roots(raw: str) -> tuple[Path, ...]:
    try:
        roots = json.loads(raw)
    except json.JSONDecodeError:
        roots = []
    if not isinstance(roots, list):
        roots = []
    return tuple(Path(item).resolve() for item in roots if isinstance(item, str))


def _allowed_directory(path: Path, roots: tuple[Path, ...]) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or not roots or not any(resolved.is_relative_to(root) for root in roots):
        raise VisionError("vision_folder_forbidden", "Folder is outside configured vision roots")
    return resolved


def _safe_filename(value: str) -> str:
    name = Path(value).name.strip()
    return name[:255] or "image"


def _write_private(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as file:
        file.write(data)


def _read_regular_file(path: Path, max_size: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as file:
        metadata = os.fstat(file.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_size:
            raise VisionError("vision_image_too_large", "Folder image exceeds the configured size limit")
        return file.read(max_size + 1)


def _prompt(mode: VisionMode, custom: str | None) -> str:
    prompts = {
        VisionMode.DESCRIBE: "Describe what is visible in the image factually. Do not invent details.",
        VisionMode.DETAILED: "Describe the image in detail using only visible facts.",
        VisionMode.OCR: "Extract visible text. Preserve useful layout where possible.",
        VisionMode.OBJECTS: "List visually detectable objects without inferring hidden facts.",
        VisionMode.GROUNDING: "Locate the requested visible object. Return normalized coordinates only when visible.",
        VisionMode.UI: "Describe visible controls, text, and interface elements. Do not interact with the computer.",
        VisionMode.CUSTOM: custom or "Describe this image factually.",
    }
    return prompts[mode] if mode is not VisionMode.CUSTOM else custom or prompts[VisionMode.CUSTOM]
