"""add wallet tables

Revision ID: 016
Revises: 015
Create Date: 2025-11-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    # Create wallets table
    op.create_table('wallets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('salon_id')
    )
    op.create_index(op.f('ix_wallets_id'), 'wallets', ['id'], unique=False)
    
    # Create wallet_transactions table
    op.create_table('wallet_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wallet_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('payment_reference', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transaction_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_transactions_id'), 'wallet_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_payment_reference'), 'wallet_transactions', ['payment_reference'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_wallet_transactions_payment_reference'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_id'), table_name='wallet_transactions')
    op.drop_table('wallet_transactions')
    op.drop_index(op.f('ix_wallets_id'), table_name='wallets')
    op.drop_table('wallets')
