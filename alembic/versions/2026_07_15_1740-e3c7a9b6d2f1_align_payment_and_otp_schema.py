"""align payment ownership and secure OTP persistence

Revision ID: e3c7a9b6d2f1
Revises: 9b8d6f4a2c13
Create Date: 2026-07-15 17:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3c7a9b6d2f1"
down_revision: Union[str, None] = "9b8d6f4a2c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("payments", "operator", existing_type=sa.String(50), nullable=True)
    op.alter_column("payments", "phone", existing_type=sa.String(20), nullable=True)
    op.create_foreign_key(
        "fk_payments_user_id_users", "payments", "users", ["user_id"], ["id"]
    )
    op.alter_column(
        "otps",
        "code",
        existing_type=sa.String(10),
        type_=sa.String(64),
        existing_nullable=False,
    )
    op.add_column(
        "otps",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("otps", "attempt_count", server_default=None)


def downgrade() -> None:
    op.drop_column("otps", "attempt_count")
    op.alter_column(
        "otps",
        "code",
        existing_type=sa.String(64),
        type_=sa.String(10),
        existing_nullable=False,
    )
    op.drop_constraint("fk_payments_user_id_users", "payments", type_="foreignkey")
    op.alter_column("payments", "phone", existing_type=sa.String(20), nullable=False)
    op.alter_column("payments", "operator", existing_type=sa.String(50), nullable=False)
