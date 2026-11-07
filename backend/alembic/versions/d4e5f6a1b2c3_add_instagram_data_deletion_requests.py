"""add_instagram_data_deletion_requests

Revision ID: d4e5f6a1b2c3
Revises: c8194ad51e7f
Create Date: 2026-11-07 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c8194ad51e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instagram_data_deletion_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('confirmation_code', sa.String(length=64), nullable=False),
        sa.Column('ig_user_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_instagram_data_deletion_requests_confirmation_code'),
        'instagram_data_deletion_requests',
        ['confirmation_code'],
        unique=True
    )
    op.create_index(
        op.f('ix_instagram_data_deletion_requests_ig_user_id'),
        'instagram_data_deletion_requests',
        ['ig_user_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_instagram_data_deletion_requests_ig_user_id'),
        table_name='instagram_data_deletion_requests'
    )
    op.drop_index(
        op.f('ix_instagram_data_deletion_requests_confirmation_code'),
        table_name='instagram_data_deletion_requests'
    )
    op.drop_table('instagram_data_deletion_requests')
