"""add product categories

Revision ID: 015
Revises: 014
Create Date: 2025-11-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Create product_categories table
    op.create_table('product_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_categories_id'), 'product_categories', ['id'], unique=False)
    
    # Add category_id and discount_percentage to products table
    op.add_column('products', sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('discount_percentage', sa.Float(), nullable=True, server_default='0'))
    op.create_foreign_key('fk_products_category_id', 'products', 'product_categories', ['category_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Remove foreign key and columns from products
    op.drop_constraint('fk_products_category_id', 'products', type_='foreignkey')
    op.drop_column('products', 'discount_percentage')
    op.drop_column('products', 'category_id')
    
    # Drop product_categories table
    op.drop_index(op.f('ix_product_categories_id'), table_name='product_categories')
    op.drop_table('product_categories')
