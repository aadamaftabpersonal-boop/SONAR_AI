"""cached answers: CACHED_LIVE responses and 'cache' attempts (T7.4)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 22:40:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_call_attempts_provider", "call_attempts", type_="check")
    op.create_check_constraint(
        "ck_call_attempts_provider", "call_attempts", "provider IN ('bolna','simulated','cache')"
    )
    op.drop_constraint("ck_responses_origin", "business_responses", type_="check")
    op.create_check_constraint(
        "ck_responses_origin",
        "business_responses",
        "data_origin IN ('LIVE_CALL','SIMULATED','CACHED_LIVE')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM business_responses WHERE data_origin = 'CACHED_LIVE'")
    op.execute("DELETE FROM call_attempts WHERE provider = 'cache'")
    op.drop_constraint("ck_responses_origin", "business_responses", type_="check")
    op.create_check_constraint(
        "ck_responses_origin", "business_responses", "data_origin IN ('LIVE_CALL','SIMULATED')"
    )
    op.drop_constraint("ck_call_attempts_provider", "call_attempts", type_="check")
    op.create_check_constraint(
        "ck_call_attempts_provider", "call_attempts", "provider IN ('bolna','simulated')"
    )
