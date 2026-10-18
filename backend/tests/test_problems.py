"""Every error is an RFC 9457 problem (application/problem+json)."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.errors import install_problem_handlers

PROBLEM = "application/problem+json"


@pytest.mark.parametrize("path", ["/nope", "/api/v1/nope", "/api/v2/health"])
def test_unknown_paths_are_404_problems(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    assert response.json() == {"type": "about:blank", "title": "Not Found", "status": 404}


def test_wrong_method_is_a_405_problem_with_the_allowed_methods(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"] == PROBLEM
    assert response.headers["allow"] == "GET"
    assert response.json() == {"type": "about:blank", "title": "Method Not Allowed", "status": 405}


class Payload(BaseModel):
    name: str = Field(min_length=1)


@pytest.fixture
def probe_client() -> TestClient:
    """A throwaway app with the problem handlers, for errors no real route can raise yet."""
    probe = FastAPI()
    install_problem_handlers(probe)

    @probe.post("/items")
    async def create_item(payload: Payload, limit: Annotated[int, Query(ge=1)] = 1) -> Payload:
        return payload

    @probe.get("/boom")
    async def boom() -> None:
        raise ValueError("secret internal detail")

    return TestClient(probe, raise_server_exceptions=False)


def test_validation_errors_are_422_problems_with_one_error_per_field(
    probe_client: TestClient,
) -> None:
    response = probe_client.post("/items?limit=0", json={"name": ""})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Unprocessable Content"
    assert body["status"] == 422
    assert {error["field"] for error in body["errors"]} == {"query.limit", "body.name"}
    assert all(error["message"] for error in body["errors"])


def test_a_malformed_json_body_is_a_422_problem(probe_client: TestClient) -> None:
    response = probe_client.post(
        "/items", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    assert response.json()["errors"][0]["field"].startswith("body")


def test_unexpected_errors_are_500_problems_without_internal_details(
    probe_client: TestClient,
) -> None:
    response = probe_client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
    }
    assert "secret" not in response.text
