"""Migrations run from the first commit and are reversible."""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_config(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", database_url)
    return Config(str(BACKEND / "alembic.ini"))


def current_revision(database_url: str) -> str | None:
    async def read() -> str | None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT version_num FROM alembic_version"))
                return result.scalar_one_or_none()
        finally:
            await engine.dispose()

    return asyncio.run(read())


def test_there_is_a_single_head_starting_from_the_baseline(alembic_config: Config) -> None:
    script = ScriptDirectory.from_config(alembic_config)

    assert len(script.get_heads()) == 1
    assert list(script.get_bases()) == ["0001"]


def test_migrations_upgrade_downgrade_and_upgrade_again(
    alembic_config: Config, database_url: str
) -> None:
    head = ScriptDirectory.from_config(alembic_config).get_current_head()

    command.upgrade(alembic_config, "head")
    assert current_revision(database_url) == head

    command.downgrade(alembic_config, "base")
    assert current_revision(database_url) is None

    command.upgrade(alembic_config, "head")
    assert current_revision(database_url) == head
