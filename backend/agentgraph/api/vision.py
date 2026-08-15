from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status

from agentgraph.api.schemas import (
    VisionAnalysisRequest,
    VisionAnalysisResponse,
    VisionAssetResponse,
    VisionFolderRequest,
    VisionFolderResponse,
)
from agentgraph.domain.remote import Permission
from agentgraph.services.remote import AuthorizationError, AuthorizationService
from agentgraph.services.vision import VisionError, VisionService

vision_router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


def _service(request: Request) -> VisionService:
    return cast(VisionService, request.app.state.vision_service)


def _authorize(request: Request, identity: str | None, permission: Permission) -> None:
    authorization = cast(AuthorizationService, request.app.state.authorization)
    try:
        principal = authorization.principal(identity)
        authorization.require(principal, permission)
    except AuthorizationError as error:
        raise HTTPException(
            403, detail={"error": {"code": "FORBIDDEN", "message": str(error), "details": {}}}
        ) from error


@vision_router.post("/assets", response_model=VisionAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    file: Annotated[UploadFile, File(description="JPEG, PNG, or WEBP image")],
    x_agentgraph_identity: str | None = Header(default=None),
) -> VisionAssetResponse:
    _authorize(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        data = await file.read(_service(request)._settings.vision_max_file_size_bytes + 1)
        asset = await _service(request).create_asset(file.filename or "image", file.content_type, data)
    except VisionError as error:
        raise _vision_http_error(error) from error
    finally:
        await file.close()
    return _asset(asset)


@vision_router.get("/assets", response_model=list[VisionAssetResponse])
async def list_assets(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[VisionAssetResponse]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return [_asset(asset) for asset in await _service(request).list_assets()]
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.get("/assets/{asset_id}", response_model=VisionAssetResponse)
async def get_asset(
    request: Request, asset_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> VisionAssetResponse:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return _asset(await _service(request).get_asset(asset_id))
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    request: Request, asset_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> None:
    _authorize(request, x_agentgraph_identity, Permission.CONTROL)
    try:
        await _service(request).delete_asset(asset_id)
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.post(
    "/assets/{asset_id}/analyses", response_model=VisionAnalysisResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_analysis(
    request: Request,
    asset_id: UUID,
    payload: VisionAnalysisRequest,
    x_agentgraph_identity: str | None = Header(default=None),
) -> VisionAnalysisResponse:
    _authorize(request, x_agentgraph_identity, Permission.EXECUTE)
    try:
        return _analysis(await _service(request).submit_analysis(asset_id, payload.mode, payload.prompt, payload.model))
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.get("/analyses", response_model=list[VisionAnalysisResponse])
async def list_analyses(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[VisionAnalysisResponse]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return [_analysis(item) for item in await _service(request).list_analyses()]
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.get("/analyses/{analysis_id}", response_model=VisionAnalysisResponse)
async def get_analysis(
    request: Request, analysis_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> VisionAnalysisResponse:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return _analysis(await _service(request).get_analysis(analysis_id))
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.get("/folders", response_model=list[VisionFolderResponse])
async def list_folders(
    request: Request, x_agentgraph_identity: str | None = Header(default=None)
) -> list[VisionFolderResponse]:
    _authorize(request, x_agentgraph_identity, Permission.READ)
    try:
        return [_folder(folder) for folder in await _service(request).list_folders()]
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.post("/folders", response_model=VisionFolderResponse, status_code=status.HTTP_201_CREATED)
async def register_folder(
    request: Request, payload: VisionFolderRequest, x_agentgraph_identity: str | None = Header(default=None)
) -> VisionFolderResponse:
    _authorize(request, x_agentgraph_identity, Permission.CONTROL)
    try:
        return _folder(await _service(request).register_folder(payload.display_name, payload.root))
    except VisionError as error:
        raise _vision_http_error(error) from error


@vision_router.post("/folders/{folder_id}/scan")
async def scan_folder(
    request: Request, folder_id: UUID, x_agentgraph_identity: str | None = Header(default=None)
) -> dict[str, int]:
    _authorize(request, x_agentgraph_identity, Permission.CONTROL)
    try:
        return await _service(request).scan_folder(folder_id)
    except VisionError as error:
        raise _vision_http_error(error) from error


def _vision_http_error(error: VisionError) -> HTTPException:
    status_code = 404 if error.code.endswith("not_found") else 403 if error.code == "vision_folder_forbidden" else 400
    return HTTPException(status_code, detail={"error": {"code": error.code, "message": str(error), "details": {}}})


def _asset(asset: object) -> VisionAssetResponse:
    return VisionAssetResponse.model_validate(asset, from_attributes=True)


def _analysis(analysis: object) -> VisionAnalysisResponse:
    return VisionAnalysisResponse.model_validate(analysis, from_attributes=True)


def _folder(folder: object) -> VisionFolderResponse:
    return VisionFolderResponse.model_validate(folder, from_attributes=True)
