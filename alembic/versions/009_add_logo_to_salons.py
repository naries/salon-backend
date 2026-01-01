"""add logo_file_id to salons

Revision ID: 009
Revises: 008
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add logo_file_id column to salons table
    op.add_column('salons', sa.Column('logo_file_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_salons_logo_file', 'salons', 'cloud_files', ['logo_file_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_salons_logo_file_id'), 'salons', ['logo_file_id'], unique=False)
    
    # Add logo_type column to track if using predefined icon or uploaded file
    op.add_column('salons', sa.Column('logo_type', sa.String(), nullable=True, server_default='icon'))
    op.execute("UPDATE salons SET logo_type = 'icon' WHERE logo_type IS NULL")
    
    # Add logo_icon_name for predefined icons
    op.add_column('salons', sa.Column('logo_icon_name', sa.String(), nullable=True, server_default='scissors'))
    op.execute("UPDATE salons SET logo_icon_name = 'scissors' WHERE logo_icon_name IS NULL")


def downgrade():
    op.drop_index(op.f('ix_salons_logo_file_id'), table_name='salons')
    op.drop_constraint('fk_salons_logo_file', 'salons', type_='foreignkey')
    op.drop_column('salons', 'logo_icon_name')
    op.drop_column('salons', 'logo_type')
    op.drop_column('salons', 'logo_file_id')
