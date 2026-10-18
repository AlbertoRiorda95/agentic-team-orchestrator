import time

import pytest

from tests.conftest import ClientFactory


def test_readiness_is_ok_when_the_database_answers(
    make_client: ClientFactory, database_url: str
) -> None:
    with make_client(database_url=database_url) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}, "version": "0.1.0"}


def test_readiness_is_down_when_the_database_refuses_connections(
    make_client: ClientFactory,
) -> None:
    with make_client() as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "status": "down",
        "checks": {"database": "failed"},
        "version": "0.1.0",
    }


def test_readiness_is_down_when_the_database_is_too_slow(
    make_client: ClientFactory, silent_database_url: str
) -> None:
    with make_client(database_url=silent_database_url, database_check_timeout=0.3) as client:
        started = time.monotonic()
        response = client.get("/api/v1/health/ready")
        elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "failed"}
    assert elapsed < 2


def test_readiness_waits_two_seconds_by_default(
    make_client: ClientFactory, silent_database_url: str
) -> None:
    with make_client(database_url=silent_database_url) as client:
        started = time.monotonic()
        response = client.get("/api/v1/health/ready")
        elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert 1.9 <= elapsed < 3


@pytest.mark.parametrize("database_url", [None, "", "  "])
def test_the_app_does_not_start_without_a_database_url(
    make_client: ClientFactory, database_url: str | None
) -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"), make_client(database_url=database_url):
        pass
