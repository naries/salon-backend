"""add_customer_password

Revision ID: 014
Revises: 013
Create Date: 2025-11-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # Add hashed_password column to customers table
    op.add_column('customers', sa.Column('hashed_password', sa.String(), nullable=True))


def downgrade():
    # Remove hashed_password column from customers table
    op.drop_column('customers', 'hashed_password')
