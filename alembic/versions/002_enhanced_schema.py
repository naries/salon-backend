"""Enhanced schema with plans and service templates

Revision ID: 002
Revises: 001
Create Date: 2025-11-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('features', sa.Text(), nullable=True),
        sa.Column('max_appointments_per_month', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)

    # Create service_templates table
    op.create_table(
        'service_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_price', sa.Integer(), nullable=True),
        sa.Column('default_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_templates_id'), 'service_templates', ['id'], unique=False)

    # Add new columns to salons table
    op.add_column('salons', sa.Column('plan_id', sa.Integer(), nullable=True))
    op.add_column('salons', sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'))
    op.create_foreign_key('fk_salons_plan_id', 'salons', 'plans', ['plan_id'], ['id'])

    # Add new columns to users table
    op.add_column('users', sa.Column('is_superadmin', sa.Integer(), nullable=True, server_default='0'))
    
    # Make salon_id nullable for superadmins
    op.alter_column('users', 'salon_id', nullable=True)


def downgrade():
    op.alter_column('users', 'salon_id', nullable=False)
    op.drop_column('users', 'is_superadmin')
    
    op.drop_constraint('fk_salons_plan_id', 'salons', type_='foreignkey')
    op.drop_column('salons', 'is_active')
    op.drop_column('salons', 'plan_id')
    
    op.drop_index(op.f('ix_service_templates_id'), table_name='service_templates')
    op.drop_table('service_templates')
    
    op.drop_index(op.f('ix_plans_id'), table_name='plans')
    op.drop_table('plans')
