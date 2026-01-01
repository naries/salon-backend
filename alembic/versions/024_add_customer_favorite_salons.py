"""Add customer favorite salons table

Revision ID: 024
Revises: 023
Create Date: 2025-12-20

This migration adds a table for customers to favorite salons.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    # Create customer_favorite_salons table
    op.create_table(
        'customer_favorite_salons',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('salon_id', sa.Integer(), sa.ForeignKey('salons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    
    # Create indexes for better performance
    op.create_index('ix_customer_favorite_salons_customer_id', 'customer_favorite_salons', ['customer_id'])
    op.create_index('ix_customer_favorite_salons_salon_id', 'customer_favorite_salons', ['salon_id'])
    
    # Create unique constraint to prevent duplicate favorites
    op.create_unique_constraint(
        'uq_customer_favorite_salons_customer_salon',
        'customer_favorite_salons',
        ['customer_id', 'salon_id']
    )


def downgrade():
    op.drop_table('customer_favorite_salons')
