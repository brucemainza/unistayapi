"""geo module schema

Revision ID: 3a1b2c4d5e6f
Revises: 9f8c7b6d5e4a
Create Date: 2026-07-10 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1b2c4d5e6f'
down_revision: Union[str, None] = '9f8c7b6d5e4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('houses', sa.Column('formatted_address', sa.Text(), nullable=True))
    op.alter_column('houses', 'coords', existing_type=sa.String(length=255), nullable=False)
    op.create_table(
        'eta_cache',
        sa.Column('house_id', sa.String(length=36), nullable=False),
        sa.Column('university_id', sa.String(length=36), nullable=False),
        sa.Column('mode', sa.String(length=10), nullable=False),
        sa.Column('duration_s', sa.Integer(), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['house_id'], ['houses.id']),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('house_id', 'university_id', 'mode', name='uix_eta_cache')
    )


def downgrade() -> None:
    op.drop_table('eta_cache')
    op.alter_column('houses', 'coords', existing_type=sa.String(length=255), nullable=True)
    op.drop_column('houses', 'formatted_address')
