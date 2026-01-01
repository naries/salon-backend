"""Add mobile device tokens table for FCM push notifications

Revision ID: 025
Revises: 024
Create Date: 2024-12-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create mobile_device_tokens table for FCM push notifications
    op.create_table(
        'mobile_device_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_type', sa.String(), nullable=False),  # "user" or "customer"
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('fcm_token', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),  # "ios" or "android"
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('device_model', sa.String(), nullable=True),
        sa.Column('app_version', sa.String(), nullable=True),
        sa.Column('is_active', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mobile_device_tokens_recipient', 'mobile_device_tokens', ['recipient_type', 'recipient_id'])
    op.create_index('ix_mobile_device_tokens_fcm_token', 'mobile_device_tokens', ['fcm_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_mobile_device_tokens_fcm_token', table_name='mobile_device_tokens')
    op.drop_index('ix_mobile_device_tokens_recipient', table_name='mobile_device_tokens')
    op.drop_table('mobile_device_tokens')
