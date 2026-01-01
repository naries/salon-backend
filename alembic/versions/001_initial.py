"""Create initial tables

Revision ID: 001
Revises: 
Create Date: 2025-11-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create salons table
    op.create_table(
        'salons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_salons_email'), 'salons', ['email'], unique=True)
    op.create_index(op.f('ix_salons_id'), 'salons', ['id'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_admin', sa.Integer(), nullable=True),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_email'), 'customers', ['email'], unique=True)
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)

    # Create services table
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)

    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('appointment_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_appointments_id'), table_name='appointments')
    op.drop_table('appointments')
    op.drop_index(op.f('ix_services_id'), table_name='services')
    op.drop_table('services')
    op.drop_index(op.f('ix_customers_id'), table_name='customers')
    op.drop_index(op.f('ix_customers_email'), table_name='customers')
    op.drop_table('customers')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_salons_id'), table_name='salons')
    op.drop_index(op.f('ix_salons_email'), table_name='salons')
    op.drop_table('salons')
