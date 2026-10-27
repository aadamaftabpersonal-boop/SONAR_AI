"""discovery (OpenStreetMap) and shop self opt-in

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 23:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("external_source", sa.Text()),
    ("external_id", sa.Text()),
    ("discovered_at", sa.DateTime(timezone=True)),
    ("opening_hours_text", sa.Text()),
    ("consent_source", sa.Text()),
    ("opt_in_requested_at", sa.DateTime(timezone=True)),
    ("preferred_language", sa.Text()),
    ("stop_token_hash", sa.Text()),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("businesses", sa.Column(name, type_, nullable=True))
    op.create_unique_constraint(
        "uq_businesses_external", "businesses", ["external_source", "external_id"]
    )
    op.create_unique_constraint("uq_businesses_stop_token", "businesses", ["stop_token_hash"])
    op.create_table(
        "opt_in_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade() -> None:
    op.drop_table("opt_in_tokens")
    op.drop_constraint("uq_businesses_stop_token", "businesses", type_="unique")
    op.drop_constraint("uq_businesses_external", "businesses", type_="unique")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("businesses", name)
