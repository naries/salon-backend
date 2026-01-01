"""add superadmin features

Revision ID: 011
Revises: 010
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Check and create superadmin_settings table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'superadmin_settings' not in inspector.get_table_names():
        op.create_table('superadmin_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('default_logo_icon', sa.String(), nullable=True),
            sa.Column('default_opening_hour', sa.Integer(), nullable=False, server_default='9'),
            sa.Column('default_closing_hour', sa.Integer(), nullable=False, server_default='18'),
            sa.Column('default_max_concurrent_slots', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Add salon_id to customers table if it doesn't exist
    if 'salon_id' not in [col['name'] for col in inspector.get_columns('customers')]:
        op.add_column('customers', sa.Column('salon_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_customers_salon_id', 'customers', 'salons', ['salon_id'], ['id'])
        
        # Update existing customers to have salon_id from their appointments
        op.execute("""
            UPDATE customers 
            SET salon_id = (
                SELECT DISTINCT salon_id 
                FROM appointments 
                WHERE appointments.customer_id = customers.id 
                LIMIT 1
            )
            WHERE salon_id IS NULL
        """)
    
    # Add deleted_at to salons table if it doesn't exist
    if 'deleted_at' not in [col['name'] for col in inspector.get_columns('salons')]:
        op.add_column('salons', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade():
    # Drop superadmin_settings table
    op.drop_table('superadmin_settings')
    
    # Remove deleted_at from salons
    op.drop_column('salons', 'deleted_at')
    
    # Remove salon_id from customers
    op.drop_constraint('fk_customers_salon_id', 'customers', type_='foreignkey')
    op.drop_column('customers', 'salon_id')
