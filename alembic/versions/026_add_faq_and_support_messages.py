"""Add FAQ and customer support messages tables

Revision ID: 026
Revises: 025
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FAQs table - managed by superadmin
    op.create_table(
        'faqs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('order_index', sa.Integer(), default=0),
        sa.Column('is_active', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on is_active for filtering
    op.create_index('ix_faqs_is_active', 'faqs', ['is_active'])
    
    # Customer support messages table
    op.create_table(
        'customer_support_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), default='pending'),  # pending, in_progress, resolved
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('responded_by', sa.Integer(), nullable=True),  # User ID of admin who responded
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_customer_support_messages_customer_id', 'customer_support_messages', ['customer_id'])
    op.create_index('ix_customer_support_messages_status', 'customer_support_messages', ['status'])


def downgrade() -> None:
    op.drop_index('ix_customer_support_messages_status', table_name='customer_support_messages')
    op.drop_index('ix_customer_support_messages_customer_id', table_name='customer_support_messages')
    op.drop_table('customer_support_messages')
    
    op.drop_index('ix_faqs_is_active', table_name='faqs')
    op.drop_table('faqs')
