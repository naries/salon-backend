"""add slot system

Revision ID: 004
Revises: 003
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add operating hours and slot configuration to salons table
    op.add_column('salons', sa.Column('opening_hour', sa.Integer(), nullable=False, server_default='9'))
    op.add_column('salons', sa.Column('closing_hour', sa.Integer(), nullable=False, server_default='18'))
    op.add_column('salons', sa.Column('max_concurrent_slots', sa.Integer(), nullable=False, server_default='3'))
    
    # Add slot_number to appointments table
    op.add_column('appointments', sa.Column('slot_number', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('appointments', 'slot_number')
    op.drop_column('salons', 'max_concurrent_slots')
    op.drop_column('salons', 'closing_hour')
    op.drop_column('salons', 'opening_hour')
