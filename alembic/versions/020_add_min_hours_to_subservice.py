"""Add min_hours to SubService

Revision ID: 020
Revises: 019
Create Date: 2025-11-26 14:43:48

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    # Add min_hours column to sub_services table
    op.add_column('sub_services', sa.Column('min_hours', sa.Integer(), server_default='1', nullable=True))


def downgrade():
    # Remove min_hours column from sub_services table
    op.drop_column('sub_services', 'min_hours')
