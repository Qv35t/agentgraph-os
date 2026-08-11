from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from agentgraph.api.schemas import (
    AgentResponse,
    CreateAgentRequest,
    HealthResponse,
    ProviderStatusResponse,
    RunAgentRequest,
    RunResponse,
)
from agentgraph.models.router import ModelRouter
from agentgraph.services.errors import AgentNotFoundError, LifecycleConflictError, RunNotFoundError
from agentgraph.services.manager import AgentManager

router = APIRouter()


def _manager(request: Request) -> AgentManager:
    return cast(AgentManager, request.app.state.agent_manager)


def _model_router(request: Request) -> ModelRouter:
    return cast(ModelRouter, request.app.state.model_router)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/providers", response_model=list[ProviderStatusResponse])
async def list_providers(request: Request) -> list[ProviderStatusResponse]:
    statuses = await _model_router(request).provider_statuses()
    return [ProviderStatusResponse.from_domain(provider) for provider in statuses]


@router.post("/api/agents/create", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: Request, payload: CreateAgentRequest) -> AgentResponse:
    agent = await _manager(request).create_agent(
        name=payload.name,
        description=payload.description,
        model_ref=payload.model_ref,
        graph_definition=payload.graph_definition.model_dump(),
    )
    return AgentResponse.from_domain(agent)


@router.get("/api/agents", response_model=list[AgentResponse])
async def list_agents(request: Request) -> list[AgentResponse]:
    return [AgentResponse.from_domain(agent) for agent in await _manager(request).list_agents()]


@router.get("/api/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(request: Request, agent_id: UUID) -> AgentResponse:
    try:
        return AgentResponse.from_domain(await _manager(request).get_agent(agent_id))
    except AgentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from error


@router.delete("/api/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(request: Request, agent_id: UUID) -> Response:
    try:
        await _manager(request).delete_agent(agent_id)
    except AgentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from error
    except LifecycleConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/agents/{agent_id}/status", response_model=AgentResponse)
async def get_agent_status(request: Request, agent_id: UUID) -> AgentResponse:
    return await get_agent(request, agent_id)


@router.post("/api/agents/run", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_agent(request: Request, payload: RunAgentRequest) -> RunResponse:
    try:
        run = await _manager(request).start_run(agent_id=payload.agent_id, input_text=payload.input_text)
    except AgentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from error
    except LifecycleConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return RunResponse.from_domain(run)


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(request: Request, run_id: UUID) -> RunResponse:
    try:
        return RunResponse.from_domain(await _manager(request).get_run(run_id))
    except RunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from error


@router.post("/api/runs/{run_id}/stop", response_model=RunResponse)
async def stop_run(request: Request, run_id: UUID) -> RunResponse:
    try:
        return RunResponse.from_domain(await _manager(request).stop_run(run_id))
    except RunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from error
    except LifecycleConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/api/agents/{agent_id}/runs", response_model=list[RunResponse])
async def list_agent_runs(request: Request, agent_id: UUID) -> list[RunResponse]:
    try:
        runs = await _manager(request).list_runs(agent_id)
    except AgentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found") from error
    return [RunResponse.from_domain(run) for run in runs]
