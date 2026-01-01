"""add support and complaints tables

Revision ID: 019
Revises: 018
Create Date: 2025-11-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    # Create support_tickets table
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('priority', sa.String(), nullable=False, server_default='normal'),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('responded_by', sa.Integer(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responded_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_support_tickets_id', 'support_tickets', ['id'])
    op.create_index('ix_support_tickets_salon_id', 'support_tickets', ['salon_id'])
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('ix_support_tickets_created_at', 'support_tickets', ['created_at'])

    # Create customer_complaints table
    op.create_table(
        'customer_complaints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('customer_phone', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('priority', sa.String(), nullable=False, server_default='normal'),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('salon_response', sa.Text(), nullable=True),
        sa.Column('responded_by', sa.Integer(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responded_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_customer_complaints_id', 'customer_complaints', ['id'])
    op.create_index('ix_customer_complaints_salon_id', 'customer_complaints', ['salon_id'])
    op.create_index('ix_customer_complaints_status', 'customer_complaints', ['status'])
    op.create_index('ix_customer_complaints_created_at', 'customer_complaints', ['created_at'])


def downgrade():
    op.drop_index('ix_customer_complaints_created_at', 'customer_complaints')
    op.drop_index('ix_customer_complaints_status', 'customer_complaints')
    op.drop_index('ix_customer_complaints_salon_id', 'customer_complaints')
    op.drop_index('ix_customer_complaints_id', 'customer_complaints')
    op.drop_table('customer_complaints')
    
    op.drop_index('ix_support_tickets_created_at', 'support_tickets')
    op.drop_index('ix_support_tickets_status', 'support_tickets')
    op.drop_index('ix_support_tickets_salon_id', 'support_tickets')
    op.drop_index('ix_support_tickets_id', 'support_tickets')
    op.drop_table('support_tickets')
