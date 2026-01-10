"""Add UUID to customers table

Revision ID: 028_add_uuid
Revises: 027_add_chat_tables
Create Date: 2026-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '028_add_uuid'
down_revision = '027_add_chat_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add UUID column to customers table
    op.add_column('customers', sa.Column('uuid', sa.String(36), nullable=True))
    
    # Generate UUIDs for existing customers using PostgreSQL's gen_random_uuid()
    # Note: Requires PostgreSQL with pgcrypto extension or PostgreSQL 13+
    op.execute("""
        UPDATE customers 
        SET uuid = gen_random_uuid()::text
        WHERE uuid IS NULL
    """)
    
    # Make UUID non-nullable and unique after populating
    op.alter_column('customers', 'uuid', nullable=False)
    op.create_unique_constraint('uq_customers_uuid', 'customers', ['uuid'])
    op.create_index('ix_customers_uuid', 'customers', ['uuid'])


def downgrade():
    op.drop_index('ix_customers_uuid', table_name='customers')
    op.drop_constraint('uq_customers_uuid', 'customers', type_='unique')
    op.drop_column('customers', 'uuid')
