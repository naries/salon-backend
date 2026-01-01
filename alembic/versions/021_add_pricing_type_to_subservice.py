"""Add pricing_type to SubService

Revision ID: 021
Revises: 020
Create Date: 2025-11-26 14:50:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade():
    # Add pricing_type column to sub_services table
    op.add_column('sub_services', sa.Column('pricing_type', sa.String(), server_default='hourly', nullable=True))
    
    # Update existing records to have 'hourly' as pricing_type
    op.execute("UPDATE sub_services SET pricing_type = 'hourly' WHERE pricing_type IS NULL")


def downgrade():
    # Remove pricing_type column from sub_services table
    op.drop_column('sub_services', 'pricing_type')
