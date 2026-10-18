"""docs/api/openapi.yaml is the FastAPI export, committed with the code."""

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

import export_openapi  # noqa: E402


@pytest.fixture
def committed() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(export_openapi.DEFAULT_OUTPUT.read_text())
    return document


def test_the_committed_contract_matches_the_export() -> None:
    assert export_openapi.main(["--check"]) == 0, "run 'make openapi' and commit it"


def test_the_contract_has_exactly_the_health_operations(committed: dict[str, Any]) -> None:
    operations = {
        path: {method: operation["operationId"] for method, operation in item.items()}
        for path, item in committed["paths"].items()
    }

    assert operations == {"/health": {"get": "health"}, "/health/ready": {"get": "readiness"}}
    assert committed["info"]["version"] == "0.1.0"
    assert committed["servers"][0]["url"] == "http://localhost:8000/api/v1"


def test_check_fails_when_the_file_is_out_of_date(tmp_path: Path) -> None:
    stale = tmp_path / "openapi.yaml"
    stale.write_text("openapi: 3.1.0\n")

    assert export_openapi.main(["--output", str(stale), "--check"]) == 1
    assert export_openapi.main(["--output", str(stale)]) == 0
    assert export_openapi.main(["--output", str(stale), "--check"]) == 0
