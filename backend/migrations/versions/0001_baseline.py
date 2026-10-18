"""baseline

Revision ID: 0001
Revises:
Create Date: 2026-10-18 16:03:07.660399

Empty baseline: no domain tables yet (foundations). Every later revision
descends from this one, so migrations run from the first commit.
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
