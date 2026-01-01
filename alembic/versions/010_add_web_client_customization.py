"""add web client customization

Revision ID: 010
Revises: 009
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Add layout_pattern column for web client layout
    op.add_column('salons', sa.Column('layout_pattern', sa.String(), nullable=True, server_default='classic'))
    op.execute("UPDATE salons SET layout_pattern = 'classic' WHERE layout_pattern IS NULL")
    
    # Add client_theme_name for web client theme (different from backoffice theme)
    op.add_column('salons', sa.Column('client_theme_name', sa.String(), nullable=True, server_default='ocean'))
    op.execute("UPDATE salons SET client_theme_name = 'ocean' WHERE client_theme_name IS NULL")
    
    # Add custom CSS for advanced customization
    op.add_column('salons', sa.Column('custom_css', sa.Text(), nullable=True))
    
    # Add primary_color and accent_color for quick color customization
    op.add_column('salons', sa.Column('primary_color', sa.String(), nullable=True))
    op.add_column('salons', sa.Column('accent_color', sa.String(), nullable=True))


def downgrade():
    op.drop_column('salons', 'accent_color')
    op.drop_column('salons', 'primary_color')
    op.drop_column('salons', 'custom_css')
    op.drop_column('salons', 'client_theme_name')
    op.drop_column('salons', 'layout_pattern')
