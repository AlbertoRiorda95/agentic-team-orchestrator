"""The version the API reports: package version, plus the short Git SHA when known."""

from importlib.metadata import version

PACKAGE_NAME = "devorchestrator-api"
SHORT_SHA_LENGTH = 7


def api_version(git_sha: str | None) -> str:
    base = version(PACKAGE_NAME)
    if not git_sha:
        return base
    return f"{base}+{git_sha.strip()[:SHORT_SHA_LENGTH]}"
