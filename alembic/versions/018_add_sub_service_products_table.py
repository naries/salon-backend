"""add sub_service_products table

Revision ID: 018
Revises: 017
Create Date: 2025-11-24

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # Create sub_service_products table
    op.create_table(
        'sub_service_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sub_service_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['sub_service_id'], ['sub_services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_service_products_sub_service_id', 'sub_service_products', ['sub_service_id'])
    op.create_index('ix_sub_service_products_product_id', 'sub_service_products', ['product_id'])


def downgrade():
    op.drop_index('ix_sub_service_products_product_id', table_name='sub_service_products')
    op.drop_index('ix_sub_service_products_sub_service_id', table_name='sub_service_products')
    op.drop_table('sub_service_products')
