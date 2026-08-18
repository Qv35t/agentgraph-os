from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from agentgraph.api.auth import _csrf, _principal
from agentgraph.api.schemas import (
    CreateSecurityApprovalRequest,
    CreateVaultCredentialRequest,
    DecideSecurityApprovalRequest,
    DeviceResponse,
    GrantResponse,
    LockdownResponse,
    RenameDeviceRequest,
    ReplaceVaultCredentialRequest,
    SecurityApprovalResponse,
    SecurityAuditResponse,
    VaultCredentialResponse,
)
from agentgraph.domain.security import LockdownState, SecurityApprovalDecision
from agentgraph.persistence.models import (
    DeviceRecord,
    GrantRecord,
    SecurityApprovalRecord,
    SecurityAuditRecord,
    SecurityStateRecord,
    VaultCredentialRecord,
)
from agentgraph.services.auth import SessionPrincipal
from agentgraph.services.security import SecurityAuthorizationError, SecurityConflictError, SecurityService
from agentgraph.services.vault import VaultError, VaultService

security_router = APIRouter(prefix="/api/v1/security", tags=["security"])


def _security(request: Request) -> SecurityService:
    service = getattr(request.app.state, "security_service", None)
    if not isinstance(service, SecurityService):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Security is unavailable")
    return service


def _vault(request: Request) -> VaultService:
    service = getattr(request.app.state, "vault_service", None)
    if not isinstance(service, VaultService):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vault is unavailable")
    return service


async def _mutation_principal(request: Request, csrf_token: str | None, origin: str | None) -> SessionPrincipal:
    principal = await _principal(request)
    await _csrf(request, principal, csrf_token, origin)
    return principal


@security_router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(request: Request) -> list[DeviceResponse]:
    principal = await _principal(request)
    return [_device_response(record) for record in await _security(request).list_devices(principal)]


@security_router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def rename_device(
    request: Request,
    device_id: str,
    payload: RenameDeviceRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> DeviceResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _device_response(await _security(request).rename_device(principal, device_id, payload.display_name))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device was not found") from error


@security_router.post("/devices/{device_id}/trust", response_model=DeviceResponse)
async def trust_device(
    request: Request,
    device_id: str,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> DeviceResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _device_response(await _security(request).trust_device(principal, device_id))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device was not found") from error
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except SecurityConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@security_router.post("/devices/{device_id}/revoke", response_model=DeviceResponse)
async def revoke_device(
    request: Request,
    device_id: str,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> DeviceResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _device_response(await _security(request).revoke_device(principal, device_id))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device was not found") from error
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/approvals", response_model=SecurityApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval(
    request: Request,
    payload: CreateSecurityApprovalRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> SecurityApprovalResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        record = await _security(request).create_approval(
            principal,
            project_id=request.app.state.settings.project_id,
            action=payload.action,
            reason=payload.reason,
            scope=payload.scope,
            expires_in_seconds=payload.expires_in_seconds,
            target=payload.target,
            run_id=payload.run_id,
            task_ref=payload.task_ref,
            risk=payload.risk,
        )
        return _approval_response(record)
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.get("/approvals", response_model=list[SecurityApprovalResponse])
async def list_approvals(
    request: Request, approval_status: str | None = Query(default=None, alias="status")
) -> list[SecurityApprovalResponse]:
    principal = await _principal(request)
    try:
        records = await _security(request).list_approvals(principal, approval_status)
        return [_approval_response(record) for record in records]
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/approvals/{approval_id}/decision", response_model=SecurityApprovalResponse)
async def decide_approval(
    request: Request,
    approval_id: str,
    payload: DecideSecurityApprovalRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> SecurityApprovalResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        record, _ = await _security(request).decide_approval(
            principal, approval_id, SecurityApprovalDecision(payload.decision)
        )
        return _approval_response(record)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval was not found") from error
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except SecurityConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@security_router.get("/grants", response_model=list[GrantResponse])
async def list_grants(request: Request) -> list[GrantResponse]:
    principal = await _principal(request)
    try:
        return [_grant_response(record) for record in await _security(request).list_grants(principal)]
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/grants/{grant_id}/revoke", response_model=GrantResponse)
async def revoke_grant(
    request: Request,
    grant_id: str,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> GrantResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _grant_response(await _security(request).revoke_grant(principal, grant_id))
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant was not found") from error
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.get("/lockdown", response_model=LockdownResponse)
async def lockdown_state(request: Request) -> LockdownResponse:
    principal = await _principal(request)
    try:
        return _lockdown_response(await _security(request).lockdown_state(principal))
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/lockdown/activate", response_model=LockdownResponse)
async def activate_lockdown(
    request: Request,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> LockdownResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _lockdown_response(await _security(request).activate_lockdown(principal))
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/lockdown/deactivate", response_model=LockdownResponse)
async def deactivate_lockdown(
    request: Request,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> LockdownResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        return _lockdown_response(await _security(request).deactivate_lockdown(principal))
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.get("/audit", response_model=list[SecurityAuditResponse])
async def list_audit(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> list[SecurityAuditResponse]:
    principal = await _principal(request)
    try:
        return [_audit_response(record) for record in await _security(request).list_audit(principal, limit)]
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.get("/vault", response_model=list[VaultCredentialResponse])
async def list_vault_credentials(request: Request) -> list[VaultCredentialResponse]:
    principal = await _principal(request)
    try:
        await _security(request).require_vault_management(principal)
        return [_vault_response(record) for record in await _vault(request).list_metadata()]
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.post("/vault", response_model=VaultCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_vault_credential(
    request: Request,
    payload: CreateVaultCredentialRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> VaultCredentialResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        await _security(request).require_vault_management(principal)
        return _vault_response(
            await _vault(request).create(
                owner_user_id=principal.user_id,
                name=payload.name,
                credential_type=payload.credential_type,
                secret=payload.secret,
            )
        )
    except (SecurityAuthorizationError, VaultError) as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@security_router.put("/vault/{credential_id}", response_model=VaultCredentialResponse)
async def replace_vault_credential(
    request: Request,
    credential_id: str,
    payload: ReplaceVaultCredentialRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> VaultCredentialResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        await _security(request).require_vault_management(principal)
        return _vault_response(await _vault(request).replace(credential_id=credential_id, secret=payload.secret))
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except VaultError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@security_router.post("/vault/{credential_id}/revoke", response_model=VaultCredentialResponse)
async def revoke_vault_credential(
    request: Request,
    credential_id: str,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> VaultCredentialResponse:
    principal = await _mutation_principal(request, x_agentgraph_csrf, origin)
    try:
        await _security(request).require_vault_management(principal)
        return _vault_response(await _vault(request).revoke(credential_id))
    except SecurityAuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except VaultError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


def _device_response(record: DeviceRecord) -> DeviceResponse:
    return DeviceResponse.model_validate(record, from_attributes=True)


def _approval_response(record: SecurityApprovalRecord) -> SecurityApprovalResponse:
    return SecurityApprovalResponse.model_validate(record, from_attributes=True)


def _grant_response(record: GrantRecord) -> GrantResponse:
    return GrantResponse.model_validate(record, from_attributes=True)


def _lockdown_response(record: SecurityStateRecord) -> LockdownResponse:
    return LockdownResponse(active=record.lockdown is LockdownState.LOCKED_DOWN, updated_at=record.updated_at)


def _audit_response(record: SecurityAuditRecord) -> SecurityAuditResponse:
    return SecurityAuditResponse(
        id=record.id,
        event_type=record.event_type,
        actor_user_id=record.actor_user_id,
        session_id=record.session_id,
        device_id=record.device_id,
        target=record.target,
        result=record.result,
        metadata=record.metadata_json,
        created_at=record.created_at,
    )


def _vault_response(record: VaultCredentialRecord) -> VaultCredentialResponse:
    return VaultCredentialResponse(
        id=record.id,
        name=record.name,
        credential_type=record.credential_type,
        revoked_at=record.revoked_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
