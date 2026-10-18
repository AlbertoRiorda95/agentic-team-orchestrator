from fastapi.testclient import TestClient

from tests.conftest import ClientFactory


def test_health_answers_ok_with_the_package_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_health_version_carries_the_short_git_sha(make_client: ClientFactory) -> None:
    with make_client(git_sha="abc1234def5678abc1234def5678abc1234def56") as client:
        response = client.get("/api/v1/health")

    assert response.json()["version"] == "0.1.0+abc1234"


def test_health_does_not_need_the_database(client: TestClient) -> None:
    # the default test database is unreachable: liveness must not care
    response = client.get("/api/v1/health")

    assert response.status_code == 200
