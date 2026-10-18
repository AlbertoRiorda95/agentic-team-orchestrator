import os
import socket
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

# Nothing listens on port 1: connections are refused right away.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://127.0.0.1:1/unreachable"

type ClientFactory = Callable[..., AbstractContextManager[TestClient]]


@pytest.fixture
def make_client() -> ClientFactory:
    """Build a client for an app with the given settings (lifespan included)."""

    @contextmanager
    def factory(
        *, database_check_timeout: float | None = None, **overrides: Any
    ) -> Iterator[TestClient]:
        values: dict[str, Any] = {"database_url": UNREACHABLE_DATABASE_URL, "git_sha": None}
        values.update(overrides)
        app_options = {}
        if database_check_timeout is not None:
            app_options["database_check_timeout"] = database_check_timeout
        app = create_app(Settings(**values), **app_options)
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client

    return factory


@pytest.fixture
def client(make_client: ClientFactory) -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


@pytest.fixture
def database_url() -> str:
    """A real PostgreSQL database, from DATABASE_URL (CI sets it)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set")
    return url


@pytest.fixture
def silent_database_url() -> Iterator[str]:
    """A server that accepts connections and never answers, like a hung database."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        yield f"postgresql+asyncpg://127.0.0.1:{port}/silent"
