"""add theme support

Revision ID: 007
Revises: 006
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add theme_name column to salons table
    op.add_column('salons', sa.Column('theme_name', sa.String(), nullable=True))
    op.execute("UPDATE salons SET theme_name = 'purple' WHERE theme_name IS NULL")
    
    # Add theme_name column to users table
    op.add_column('users', sa.Column('theme_name', sa.String(), nullable=True))
    op.execute("UPDATE users SET theme_name = 'purple' WHERE theme_name IS NULL")


def downgrade():
    op.drop_column('users', 'theme_name')
    op.drop_column('salons', 'theme_name')
