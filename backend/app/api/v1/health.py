"""Liveness and readiness."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import database_is_ready

type HealthStatus = Literal["ok", "degraded", "down"]
type CheckStatus = Literal["ok", "failed"]


class Health(BaseModel):
    """Health of the API. Optional fields are omitted, never null."""

    status: HealthStatus
    checks: dict[str, CheckStatus] | SkipJsonSchema[None] = Field(
        default=None, description="One entry per readiness check, e.g. database."
    )
    version: str | SkipJsonSchema[None] = Field(
        default=None,
        description="API package version, plus +<short sha> when GIT_SHA is set.",
        examples=["0.1.0+abc1234"],
    )


def get_version(request: Request) -> str:
    version: str = request.app.state.version
    return version


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.engine
    return engine


def get_database_check_timeout(request: Request) -> float:
    timeout: float = request.app.state.database_check_timeout
    return timeout


VersionDep = Annotated[str, Depends(get_version)]
EngineDep = Annotated[AsyncEngine, Depends(get_engine)]
DatabaseCheckTimeoutDep = Annotated[float, Depends(get_database_check_timeout)]

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    operation_id="health",
    summary="Liveness",
    description="Always 200 while the process serves requests.",
    response_model_exclude_none=True,
)
async def health(version: VersionDep) -> Health:
    return Health(status="ok", version=version)


@router.get(
    "/ready",
    operation_id="readiness",
    summary="Readiness: database",
    description="503 when a check fails. The database check is `SELECT 1` within 2 s.",
    response_model_exclude_none=True,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": Health, "description": "Not ready"}},
)
async def readiness(
    response: Response,
    engine: EngineDep,
    time_limit: DatabaseCheckTimeoutDep,
    version: VersionDep,
) -> Health:
    database_ok = await database_is_ready(engine, time_limit)
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(
        status="ok" if database_ok else "down",
        checks={"database": "ok" if database_ok else "failed"},
        version=version,
    )
