"""add sub services

Revision ID: 005
Revises: 004
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sub_services table
    op.create_table(
        'sub_services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hourly_rate', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sub_services_id'), 'sub_services', ['id'], unique=False)
    
    # Add sub_service_id and hours to appointments table
    op.add_column('appointments', sa.Column('sub_service_id', sa.Integer(), nullable=True))
    op.add_column('appointments', sa.Column('hours', sa.Float(), nullable=False, server_default='1.0'))
    op.create_foreign_key('fk_appointments_sub_service', 'appointments', 'sub_services', ['sub_service_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_appointments_sub_service', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'hours')
    op.drop_column('appointments', 'sub_service_id')
    op.drop_index(op.f('ix_sub_services_id'), table_name='sub_services')
    op.drop_table('sub_services')
