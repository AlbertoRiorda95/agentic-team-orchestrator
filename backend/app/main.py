"""Application factory.

The public API is a sub-application mounted at /api/v1, so its OpenAPI document
lists paths relative to the server URL (/health, not /api/v1/health).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health
from app.db import create_engine
from app.errors import install_problem_handlers
from app.settings import Settings
from app.version import api_version

API_PREFIX = "/api/v1"
API_TITLE = "DevOrchestrator API"
LOCAL_SERVER = {"url": "http://localhost:8000/api/v1", "description": "local development"}
DATABASE_CHECK_TIMEOUT_SECONDS = 2.0
CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
CORS_HEADERS = ["Authorization", "Content-Type", "Last-Event-ID"]


def create_api(version: str, database_check_timeout: float) -> FastAPI:
    """The /api/v1 application, the one the contract describes."""
    api = FastAPI(
        title=API_TITLE,
        version=version.split("+", 1)[0],
        servers=[LOCAL_SERVER],
        root_path_in_servers=False,
    )
    api.state.version = version
    api.state.database_check_timeout = database_check_timeout
    install_problem_handlers(api)
    api.include_router(health.router)
    return api


def create_app(
    settings: Settings | None = None,
    *,
    database_check_timeout: float = DATABASE_CHECK_TIMEOUT_SECONDS,
) -> FastAPI:
    settings = settings or Settings()
    version = api_version(settings.git_sha)
    api = create_api(version, database_check_timeout)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # mounted apps get no lifespan of their own: the engine is set up here
        if settings.database_url is None:
            raise RuntimeError("DATABASE_URL is not set")
        engine = create_engine(settings.database_url.get_secret_value())
        api.state.engine = engine
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title=API_TITLE, version=version, openapi_url=None, lifespan=lifespan)
    install_problem_handlers(app)
    # Expo web runs on another origin; the web app goes through the Vite proxy
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
        allow_credentials=False,  # bearer tokens, no cookies
    )
    app.mount(API_PREFIX, api)
    return app


def contract() -> dict[str, Any]:
    """The OpenAPI document of /api/v1, as exported to docs/api/openapi.yaml."""
    return create_api(api_version(git_sha=None), DATABASE_CHECK_TIMEOUT_SECONDS).openapi()


# entrypoint of `fastapi dev` / `fastapi run` (pyproject.toml, [tool.fastapi])
app = create_app()
