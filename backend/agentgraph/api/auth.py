from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from agentgraph.api.schemas import (
    AuthPrincipalResponse,
    BootstrapRequest,
    PasskeyAuthenticationOptionsRequest,
    PasskeyRegistrationOptionsRequest,
    PasskeyVerificationRequest,
    TotpConfirmRequest,
    TotpEnrollmentResponse,
    TotpVerifyRequest,
    WebAuthnOptionsResponse,
)
from agentgraph.services.auth import (
    AuthenticationConflictError,
    AuthenticationError,
    AuthService,
    SessionPrincipal,
    SessionTokens,
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _service(request: Request) -> AuthService:
    service = getattr(request.app.state, "auth_service", None)
    if not isinstance(service, AuthService):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is unavailable")
    return service


async def _principal(request: Request) -> SessionPrincipal:
    try:
        session_token = request.cookies.get(request.app.state.settings.session_cookie_name)
        return await _service(request).principal_from_session_token(session_token)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


async def _csrf(request: Request, principal: SessionPrincipal, csrf_token: str | None, origin: str | None) -> None:
    try:
        await _service(request).require_csrf(principal, csrf_token, origin)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@auth_router.post("/bootstrap", response_model=WebAuthnOptionsResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(request: Request, payload: BootstrapRequest) -> WebAuthnOptionsResponse:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap requires a loopback connection")
    try:
        result = await _service(request).bootstrap(
            username=payload.username,
            bootstrap_secret=payload.bootstrap_secret,
            device_name=payload.device_name,
        )
        return WebAuthnOptionsResponse.model_validate(result)
    except AuthenticationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@auth_router.post("/passkeys/registration/options", response_model=WebAuthnOptionsResponse)
async def passkey_registration_options(
    request: Request,
    payload: PasskeyRegistrationOptionsRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> WebAuthnOptionsResponse:
    principal = await _principal(request)
    await _csrf(request, principal, x_agentgraph_csrf, origin)
    try:
        return WebAuthnOptionsResponse.model_validate(
            await _service(request).begin_passkey_registration(principal, payload.device_name)
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@auth_router.post("/passkeys/registration/verify", response_model=AuthPrincipalResponse)
async def passkey_registration_verify(
    request: Request,
    response: Response,
    payload: PasskeyVerificationRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> AuthPrincipalResponse:
    session_token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if session_token:
        principal = await _principal(request)
        await _csrf(request, principal, x_agentgraph_csrf, origin)
    try:
        tokens = await _service(request).finish_passkey_registration(
            challenge_id=payload.challenge_id,
            credential=payload.credential,
        )
    except AuthenticationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    _set_session_cookie(request, response, tokens)
    return _principal_response(tokens.principal)


@auth_router.post("/passkeys/authentication/options", response_model=WebAuthnOptionsResponse)
async def passkey_authentication_options(
    request: Request,
    payload: PasskeyAuthenticationOptionsRequest,
) -> WebAuthnOptionsResponse:
    try:
        return WebAuthnOptionsResponse.model_validate(
            await _service(request).begin_passkey_authentication(username=payload.username)
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@auth_router.post("/passkeys/authentication/verify", response_model=AuthPrincipalResponse)
async def passkey_authentication_verify(
    request: Request,
    response: Response,
    payload: PasskeyVerificationRequest,
) -> AuthPrincipalResponse:
    try:
        tokens = await _service(request).finish_passkey_authentication(
            challenge_id=payload.challenge_id,
            credential=payload.credential,
        )
    except AuthenticationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    _set_session_cookie(request, response, tokens)
    return _principal_response(tokens.principal)


@auth_router.get("/session", response_model=AuthPrincipalResponse)
async def current_session(request: Request) -> AuthPrincipalResponse:
    return _principal_response(await _principal(request))


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> Response:
    principal = await _principal(request)
    await _csrf(request, principal, x_agentgraph_csrf, origin)
    await _service(request).logout(principal)
    response.delete_cookie(request.app.state.settings.session_cookie_name, path="/")
    return response


@auth_router.post("/totp/enrollment", response_model=TotpEnrollmentResponse)
async def begin_totp_enrollment(
    request: Request,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> TotpEnrollmentResponse:
    principal = await _principal(request)
    await _csrf(request, principal, x_agentgraph_csrf, origin)
    return TotpEnrollmentResponse.model_validate(await _service(request).begin_totp_enrollment(principal))


@auth_router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_totp_enrollment(
    request: Request,
    payload: TotpConfirmRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> Response:
    principal = await _principal(request)
    await _csrf(request, principal, x_agentgraph_csrf, origin)
    try:
        await _service(request).confirm_totp_enrollment(principal, secret=payload.secret, code=payload.code)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.post("/totp/verify", response_model=AuthPrincipalResponse)
async def verify_totp(
    request: Request,
    payload: TotpVerifyRequest,
    x_agentgraph_csrf: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> AuthPrincipalResponse:
    principal = await _principal(request)
    await _csrf(request, principal, x_agentgraph_csrf, origin)
    try:
        return _principal_response(await _service(request).verify_totp(principal, payload.code))
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


def _set_session_cookie(request: Request, response: Response, tokens: SessionTokens) -> None:
    response.set_cookie(
        key=request.app.state.settings.session_cookie_name,
        value=tokens.session_token,
        max_age=request.app.state.settings.session_ttl_seconds,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )


def _principal_response(principal: SessionPrincipal) -> AuthPrincipalResponse:
    return AuthPrincipalResponse(
        user_id=principal.user_id,
        username=principal.username,
        role=principal.role.value,
        session_id=principal.session_id,
        device_id=principal.device_id,
        device_trust=principal.device_trust.value,
        authentication_strength=principal.authentication_strength.value,
        csrf_token=principal.csrf_token,
    )
