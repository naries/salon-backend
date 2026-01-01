"""add cloud_files table

Revision ID: 008
Revises: 007
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Create cloud_files table
    op.create_table(
        'cloud_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cloud_files_id'), 'cloud_files', ['id'], unique=False)
    op.create_index(op.f('ix_cloud_files_uploaded_by'), 'cloud_files', ['uploaded_by'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_cloud_files_uploaded_by'), table_name='cloud_files')
    op.drop_index(op.f('ix_cloud_files_id'), table_name='cloud_files')
    op.drop_table('cloud_files')
