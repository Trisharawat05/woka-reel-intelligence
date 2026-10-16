"""add_granted_permissions_to_instagram_accounts

Revision ID: c8194ad51e7f
Revises: bd03f60aa48b
Create Date: 2026-10-16 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8194ad51e7f'
down_revision: Union[str, Sequence[str], None] = 'bd03f60aa48b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'instagram_accounts',
        sa.Column('granted_permissions', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('instagram_accounts', 'granted_permissions')
