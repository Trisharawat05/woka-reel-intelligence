"""add_universal_video_ingestion_fields

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-11-13 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reel_analysis_jobs', sa.Column('detected_platform', sa.String(length=50), nullable=True))
    op.add_column('reel_analysis_jobs', sa.Column('platform_video_id', sa.String(length=100), nullable=True))
    op.add_column('reel_analysis_jobs', sa.Column('retrieval_status', sa.String(length=50), nullable=True))
    op.add_column('reel_analysis_jobs', sa.Column('next_action', sa.String(length=50), nullable=True))
    op.add_column('reel_analysis_jobs', sa.Column('next_action_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('reel_analysis_jobs', 'next_action_url')
    op.drop_column('reel_analysis_jobs', 'next_action')
    op.drop_column('reel_analysis_jobs', 'retrieval_status')
    op.drop_column('reel_analysis_jobs', 'platform_video_id')
    op.drop_column('reel_analysis_jobs', 'detected_platform')
