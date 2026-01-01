"""add billing cycle and pricing

Revision ID: 006
Revises: 005
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Add monthly_price and yearly_price to plans table
    op.add_column('plans', sa.Column('monthly_price', sa.Integer(), nullable=True))
    op.add_column('plans', sa.Column('yearly_price', sa.Integer(), nullable=True))
    
    # Copy existing price to monthly_price for existing records
    op.execute("UPDATE plans SET monthly_price = price WHERE monthly_price IS NULL")
    op.execute("UPDATE plans SET yearly_price = 0 WHERE yearly_price IS NULL")
    
    # Make columns non-nullable after setting defaults
    op.alter_column('plans', 'monthly_price', nullable=False, server_default='0')
    op.alter_column('plans', 'yearly_price', nullable=False, server_default='0')
    
    # Add billing_cycle and auto_debit to salons table
    op.add_column('salons', sa.Column('billing_cycle', sa.String(), nullable=True))
    op.add_column('salons', sa.Column('auto_debit', sa.Integer(), nullable=True))
    
    # Set defaults for existing records
    op.execute("UPDATE salons SET billing_cycle = 'monthly' WHERE billing_cycle IS NULL")
    op.execute("UPDATE salons SET auto_debit = 0 WHERE auto_debit IS NULL")
    
    # Make columns non-nullable after setting defaults
    op.alter_column('salons', 'billing_cycle', nullable=False, server_default='monthly')
    op.alter_column('salons', 'auto_debit', nullable=False, server_default='0')


def downgrade():
    op.drop_column('salons', 'auto_debit')
    op.drop_column('salons', 'billing_cycle')
    op.drop_column('plans', 'yearly_price')
    op.drop_column('plans', 'monthly_price')
