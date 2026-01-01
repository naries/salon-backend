"""add subscriptions and activity logs tables

Revision ID: add_subscriptions_activity_logs
Revises: 
Create Date: 2025-11-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_subscriptions_activity_logs'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Create subscriptions table if it doesn't exist
    if 'subscriptions' not in inspector.get_table_names():
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('salon_id', sa.Integer(), nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(), nullable=True, server_default='active'),
            sa.Column('billing_cycle', sa.String(), nullable=True, server_default='monthly'),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('start_date', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.Column('end_date', sa.DateTime(), nullable=True),
            sa.Column('auto_renew', sa.Integer(), nullable=True, server_default='1'),
            sa.Column('cancelled_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
            sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
        op.create_index(op.f('ix_subscriptions_salon_id'), 'subscriptions', ['salon_id'], unique=False)
        op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)

    # Create activity_logs table if it doesn't exist
    if 'activity_logs' not in inspector.get_table_names():
        op.create_table(
            'activity_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('salon_id', sa.Integer(), nullable=True),
            sa.Column('action', sa.String(), nullable=False),
            sa.Column('entity_type', sa.String(), nullable=True),
            sa.Column('entity_id', sa.Integer(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(), nullable=True),
            sa.Column('user_agent', sa.String(), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_activity_logs_id'), 'activity_logs', ['id'], unique=False)
        op.create_index(op.f('ix_activity_logs_user_id'), 'activity_logs', ['user_id'], unique=False)
        op.create_index(op.f('ix_activity_logs_salon_id'), 'activity_logs', ['salon_id'], unique=False)
        op.create_index(op.f('ix_activity_logs_action'), 'activity_logs', ['action'], unique=False)
        op.create_index(op.f('ix_activity_logs_entity_type'), 'activity_logs', ['entity_type'], unique=False)
        op.create_index(op.f('ix_activity_logs_created_at'), 'activity_logs', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_activity_logs_created_at'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_entity_type'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_action'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_salon_id'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_user_id'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_id'), table_name='activity_logs')
    op.drop_table('activity_logs')
    
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_salon_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
