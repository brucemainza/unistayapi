"""add user_id and last_event_id to payments

Revision ID: 6f3a9c2e8d4b
Revises: a71ae1e8ec58
Create Date: 2026-07-14 12:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6f3a9c2e8d4b'
down_revision: Union[str, None] = 'a71ae1e8ec58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'payments',
        sa.Column('user_id', sa.String(36), nullable=True),
    )
    op.add_column(
        'payments',
        sa.Column('last_event_id', sa.String(255), nullable=True),
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'], unique=False)
    op.create_index('ix_payments_last_event_id', 'payments', ['last_event_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_payments_last_event_id', table_name='payments')
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_column('payments', 'last_event_id')
    op.drop_column('payments', 'user_id')
