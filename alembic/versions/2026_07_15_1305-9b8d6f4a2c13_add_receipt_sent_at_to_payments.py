"""add receipt_sent_at to payments

Revision ID: 9b8d6f4a2c13
Revises: 6f3a9c2e8d4b
Create Date: 2026-07-15 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b8d6f4a2c13"
down_revision: Union[str, None] = "6f3a9c2e8d4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("receipt_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "receipt_sent_at")
