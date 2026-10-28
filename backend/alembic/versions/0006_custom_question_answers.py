"""custom question answers on business responses (D-062)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 20:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "business_responses",
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("business_responses", sa.Column("rank_value", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("business_responses", "rank_value")
    op.drop_column("business_responses", "answers")
