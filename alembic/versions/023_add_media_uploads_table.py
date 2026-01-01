"""add media uploads table

Revision ID: 023
Revises: 022
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'media_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('gcs_path', sa.String(), nullable=True),
        sa.Column('public_url', sa.String(), nullable=True),
        sa.Column('bucket_name', sa.String(), nullable=True),
        sa.Column('folder', sa.String(), nullable=False, server_default='uploads'),
        sa.Column('salon_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processing_started_at', DateTime, nullable=True),
        sa.Column('completed_at', DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_media_uploads_id', 'media_uploads', ['id'])
    op.create_index('ix_media_uploads_status', 'media_uploads', ['status'])
    op.create_index('ix_media_uploads_salon_id', 'media_uploads', ['salon_id'])
    op.create_index('ix_media_uploads_created_at', 'media_uploads', ['created_at'])


def downgrade():
    op.drop_index('ix_media_uploads_created_at', 'media_uploads')
    op.drop_index('ix_media_uploads_salon_id', 'media_uploads')
    op.drop_index('ix_media_uploads_status', 'media_uploads')
    op.drop_index('ix_media_uploads_id', 'media_uploads')
    op.drop_table('media_uploads')
