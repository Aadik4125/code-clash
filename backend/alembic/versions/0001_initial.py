"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=24), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'recordings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('session_number', sa.Integer(), nullable=False),
        sa.Column('recording_date', sa.Date(), nullable=False),
        sa.Column('storage_uri', sa.String(length=500), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('processing_status', sa.String(length=40), nullable=False, server_default='queued'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'feature_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('recording_id', sa.Integer(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('extractor', sa.String(length=40), nullable=False, server_default='librosa'),
        sa.Column('acoustic_features', sa.JSON(), nullable=False),
        sa.Column('temporal_features', sa.JSON(), nullable=False),
        sa.Column('linguistic_features', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'wellness_scores',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('recording_id', sa.Integer(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('risk_level', sa.String(length=32), nullable=False),
        sa.Column('rule_breakdown', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'weak_labels',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('recording_id', sa.Integer(), sa.ForeignKey('recordings.id'), nullable=False, index=True),
        sa.Column('stress_score', sa.Integer(), nullable=True),
        sa.Column('survey_payload', sa.JSON(), nullable=False),
        sa.Column('cognitive_test_payload', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='self_report'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'dataset_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version_name', sa.String(length=64), nullable=False, unique=True),
        sa.Column('dvc_tag', sa.String(length=128), nullable=True),
        sa.Column('storage_uri', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('dataset_versions')
    op.drop_table('weak_labels')
    op.drop_table('wellness_scores')
    op.drop_table('feature_snapshots')
    op.drop_table('recordings')
    op.drop_table('users')
