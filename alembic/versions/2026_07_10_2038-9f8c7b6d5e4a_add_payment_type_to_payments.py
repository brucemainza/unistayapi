"""add payment_type to payments

Revision ID: 9f8c7b6d5e4a
Revises: 6b380577949e
Create Date: 2026-07-10 20:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f8c7b6d5e4a'
down_revision: Union[str, None] = '6b380577949e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'payments',
        sa.Column('payment_type', sa.String(length=20), server_default='mobile-money', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('payments', 'payment_type')
