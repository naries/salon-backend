"""add bank accounts and withdrawals tables

Revision ID: 017
Revises: 016
Create Date: 2025-11-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Create bank_accounts table
    op.create_table('bank_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('account_name', sa.String(), nullable=False),
        sa.Column('account_number', sa.String(), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('bank_code', sa.String(), nullable=True),
        sa.Column('is_default', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_verified', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bank_accounts_id'), 'bank_accounts', ['id'], unique=False)
    
    # Create withdrawals table
    op.create_table('withdrawals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wallet_id', sa.Integer(), nullable=False),
        sa.Column('bank_account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('reference', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('transaction_reference', sa.String(), nullable=True),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id'], ),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference')
    )
    op.create_index(op.f('ix_withdrawals_id'), 'withdrawals', ['id'], unique=False)
    op.create_index(op.f('ix_withdrawals_reference'), 'withdrawals', ['reference'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_withdrawals_reference'), table_name='withdrawals')
    op.drop_index(op.f('ix_withdrawals_id'), table_name='withdrawals')
    op.drop_table('withdrawals')
    op.drop_index(op.f('ix_bank_accounts_id'), table_name='bank_accounts')
    op.drop_table('bank_accounts')
