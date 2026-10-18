import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from tests.conftest import UNREACHABLE_DATABASE_URL, ClientFactory

EXPO_WEB = "http://localhost:8081"


def preflight(client: TestClient, origin: str) -> dict[str, str]:
    response = client.options(
        "/api/v1/health/ready",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return dict(response.headers)


def test_expo_web_is_allowed_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": EXPO_WEB})

    assert response.headers["access-control-allow-origin"] == EXPO_WEB
    assert preflight(client, EXPO_WEB)["access-control-allow-origin"] == EXPO_WEB


def test_other_origins_are_not_allowed(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-origin" not in preflight(client, "https://evil.example")


def test_cors_origins_come_from_the_environment_comma_separated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE_DATABASE_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example")

    with TestClient(create_app(Settings())) as client:
        allowed = client.get("/api/v1/health", headers={"Origin": "http://b.example"})
        default = client.get("/api/v1/health", headers={"Origin": EXPO_WEB})

    assert allowed.headers["access-control-allow-origin"] == "http://b.example"
    assert "access-control-allow-origin" not in default.headers


def test_errors_carry_cors_headers_too(make_client: ClientFactory) -> None:
    # the status page must be able to read a 503 from another origin
    with make_client() as client:
        response = client.get("/api/v1/health/ready", headers={"Origin": EXPO_WEB})

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == EXPO_WEB
