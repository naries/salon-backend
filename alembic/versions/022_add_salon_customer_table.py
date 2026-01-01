"""Add SalonCustomer table and update Customer for platform-wide customers

Revision ID: 022
Revises: 021
Create Date: 2025-12-04

This migration:
1. Adds platform fields to customers table (is_verified, platform_joined_at)
2. Creates salon_customers junction table for salon-customer relationships
3. Migrates existing customer-salon relationships to salon_customers table
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add platform fields to customers table
    op.add_column('customers', sa.Column('is_verified', sa.Integer(), server_default='0', nullable=True))
    op.add_column('customers', sa.Column('platform_joined_at', sa.DateTime(), nullable=True))
    
    # Set platform_joined_at to created_at for existing customers
    op.execute("UPDATE customers SET platform_joined_at = created_at WHERE platform_joined_at IS NULL")
    
    # Step 2: Create salon_customers junction table
    op.create_table(
        'salon_customers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('salon_id', sa.Integer(), sa.ForeignKey('salons.id'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('source', sa.String(), server_default='appointment', nullable=True),  # "appointment", "purchase", "manual"
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('loyalty_points', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_spent', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_appointments', sa.Integer(), server_default='0', nullable=True),
        sa.Column('is_favorite', sa.Integer(), server_default='0', nullable=True),
        sa.Column('first_interaction_at', sa.DateTime(), nullable=True),
        sa.Column('last_interaction_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    
    # Create indexes for better performance
    op.create_index('ix_salon_customers_salon_id', 'salon_customers', ['salon_id'])
    op.create_index('ix_salon_customers_customer_id', 'salon_customers', ['customer_id'])
    
    # Create unique constraint to prevent duplicate salon-customer relationships
    op.create_unique_constraint(
        'uq_salon_customer',
        'salon_customers',
        ['salon_id', 'customer_id']
    )
    
    # Step 3: Migrate existing customer-salon relationships
    # For each customer with a salon_id, create a salon_customers entry
    op.execute("""
        INSERT INTO salon_customers (salon_id, customer_id, source, first_interaction_at, last_interaction_at, created_at)
        SELECT salon_id, id, 'manual', created_at, created_at, created_at
        FROM customers
        WHERE salon_id IS NOT NULL
    """)
    
    # Step 4: Calculate total_appointments for migrated records
    op.execute("""
        UPDATE salon_customers 
        SET total_appointments = (
            SELECT COUNT(*) FROM appointments 
            WHERE appointments.customer_id = salon_customers.customer_id 
            AND appointments.salon_id = salon_customers.salon_id
        )
    """)
    
    # Step 5: Calculate total_spent from orders
    op.execute("""
        UPDATE salon_customers 
        SET total_spent = COALESCE((
            SELECT SUM(total_amount) FROM orders 
            WHERE orders.customer_id = salon_customers.customer_id 
            AND orders.salon_id = salon_customers.salon_id
            AND orders.status = 'paid'
        ), 0)
    """)
    
    # Step 6: Update last_interaction_at based on most recent appointment or order
    op.execute("""
        UPDATE salon_customers 
        SET last_interaction_at = COALESCE(
            (SELECT MAX(created_at) FROM appointments 
             WHERE appointments.customer_id = salon_customers.customer_id 
             AND appointments.salon_id = salon_customers.salon_id),
            salon_customers.first_interaction_at
        )
    """)


def downgrade():
    # Drop salon_customers table
    op.drop_constraint('uq_salon_customer', 'salon_customers', type_='unique')
    op.drop_index('ix_salon_customers_customer_id', 'salon_customers')
    op.drop_index('ix_salon_customers_salon_id', 'salon_customers')
    op.drop_table('salon_customers')
    
    # Remove platform fields from customers
    op.drop_column('customers', 'platform_joined_at')
    op.drop_column('customers', 'is_verified')
