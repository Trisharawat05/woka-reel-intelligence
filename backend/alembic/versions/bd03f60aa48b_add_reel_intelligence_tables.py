"""add_reel_intelligence_tables

Revision ID: bd03f60aa48b
Revises: ba8433934b4b
Create Date: 2026-10-16 15:41:41.906401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd03f60aa48b'
down_revision: Union[str, Sequence[str], None] = 'ba8433934b4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. reel_media_assets
    op.create_table(
        'reel_media_assets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='video/mp4'),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('resolution_width', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolution_height', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('aspect_ratio', sa.String(length=20), nullable=False, server_default='9:16'),
        sa.Column('fps', sa.Float(), nullable=False, server_default='30.0'),
        sa.Column('thumbnail_path', sa.Text(), nullable=True),
        sa.Column('is_temporary', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reel_media_assets_workspace_id'), 'reel_media_assets', ['workspace_id'], unique=False)

    # 2. reel_reports (created before foreign key link from reel_analysis_jobs)
    op.create_table(
        'reel_reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Instagram Reel Analysis'),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('analysis_mode', sa.String(length=40), nullable=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('creative_quality_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('performance_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('growth_conversion_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('viral_potential_estimate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('score_breakdown_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('calculated_metrics_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('video_intelligence_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('timeline_findings_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('prioritized_action_plan_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('creative_alternatives_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('provenance_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    op.create_index(op.f('ix_reel_reports_workspace_id'), 'reel_reports', ['workspace_id'], unique=False)

    # 3. reel_analysis_jobs
    op.create_table(
        'reel_analysis_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_mode', sa.String(length=40), nullable=False),
        sa.Column('input_type', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='QUEUED'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stage_message', sa.String(length=255), nullable=False, server_default='Queued for analysis'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_media_id', sa.String(length=100), nullable=True),
        sa.Column('video_asset_id', sa.String(length=36), nullable=True),
        sa.Column('report_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['video_asset_id'], ['reel_media_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_id'], ['reel_reports.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reel_analysis_jobs_workspace_id'), 'reel_analysis_jobs', ['workspace_id'], unique=False)

    # 4. reel_metric_snapshots
    op.create_table(
        'reel_metric_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('snapshot_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reach_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('impressions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('saves_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_watch_time_seconds', sa.Float(), nullable=True),
        sa.Column('total_watch_time_seconds', sa.Float(), nullable=True),
        sa.Column('reposts_count', sa.Integer(), nullable=True),
        sa.Column('follows_attributed', sa.Integer(), nullable=True),
        sa.Column('profile_activity', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='PUBLIC_SCRAPE_FALLBACK'),
        sa.Column('data_completeness', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('limitations_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['job_id'], ['reel_analysis_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reel_metric_snapshots_workspace_id'), 'reel_metric_snapshots', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_reel_metric_snapshots_job_id'), 'reel_metric_snapshots', ['job_id'], unique=False)

    # 5. reel_comparisons
    op.create_table(
        'reel_comparisons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('report_ids', sa.Text(), nullable=False),
        sa.Column('comparison_summary_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reel_comparisons_workspace_id'), 'reel_comparisons', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('reel_comparisons')
    op.drop_table('reel_metric_snapshots')
    op.drop_table('reel_analysis_jobs')
    op.drop_table('reel_reports')
    op.drop_table('reel_media_assets')
