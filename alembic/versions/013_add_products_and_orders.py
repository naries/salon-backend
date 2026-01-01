"""add products and orders tables

Revision ID: 013
Revises: 012
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Create products table
    if 'products' not in inspector.get_table_names():
        op.create_table('products',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('salon_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('price', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('image_file_id', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
            sa.ForeignKeyConstraint(['image_file_id'], ['cloud_files.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
        op.create_index(op.f('ix_products_salon_id'), 'products', ['salon_id'], unique=False)
    
    # Create carts table
    if 'carts' not in inspector.get_table_names():
        op.create_table('carts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('salon_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
            sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_carts_id'), 'carts', ['id'], unique=False)
        op.create_index(op.f('ix_carts_customer_id'), 'carts', ['customer_id'], unique=False)
    
    # Create cart_items table
    if 'cart_items' not in inspector.get_table_names():
        op.create_table('cart_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cart_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_cart_items_id'), 'cart_items', ['id'], unique=False)
    
    # Create orders table
    if 'orders' not in inspector.get_table_names():
        op.create_table('orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('salon_id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('order_number', sa.String(), nullable=False),
            sa.Column('total_amount', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('payment_method', sa.String(), nullable=True),
            sa.Column('payment_reference', sa.String(), nullable=True),
            sa.Column('payment_data', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)
        op.create_index(op.f('ix_orders_order_number'), 'orders', ['order_number'], unique=True)
        op.create_index(op.f('ix_orders_payment_reference'), 'orders', ['payment_reference'], unique=True)
    
    # Create order_items table
    if 'order_items' not in inspector.get_table_names():
        op.create_table('order_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('price_at_purchase', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_order_items_id'), 'order_items', ['id'], unique=False)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Drop tables in reverse order
    if 'order_items' in inspector.get_table_names():
        op.drop_index(op.f('ix_order_items_id'), table_name='order_items')
        op.drop_table('order_items')
    
    if 'orders' in inspector.get_table_names():
        op.drop_index(op.f('ix_orders_payment_reference'), table_name='orders')
        op.drop_index(op.f('ix_orders_order_number'), table_name='orders')
        op.drop_index(op.f('ix_orders_id'), table_name='orders')
        op.drop_table('orders')
    
    if 'cart_items' in inspector.get_table_names():
        op.drop_index(op.f('ix_cart_items_id'), table_name='cart_items')
        op.drop_table('cart_items')
    
    if 'carts' in inspector.get_table_names():
        op.drop_index(op.f('ix_carts_customer_id'), table_name='carts')
        op.drop_index(op.f('ix_carts_id'), table_name='carts')
        op.drop_table('carts')
    
    if 'products' in inspector.get_table_names():
        op.drop_index(op.f('ix_products_salon_id'), table_name='products')
        op.drop_index(op.f('ix_products_id'), table_name='products')
        op.drop_table('products')
