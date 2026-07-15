"""add soft delete to houses

Revision ID: a71ae1e8ec58
Revises: 0e900f058b3d
Create Date: 2026-07-11 11:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a71ae1e8ec58'
down_revision: Union[str, None] = '0e900f058b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('houses', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('houses', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_houses_is_deleted', 'houses', ['is_deleted'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_houses_is_deleted', table_name='houses')
    op.drop_column('houses', 'deleted_at')
    op.drop_column('houses', 'is_deleted')
