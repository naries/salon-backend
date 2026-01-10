"""
Add Chat System Tables

Revision ID: 027_add_chat_tables
Revises: 026
Create Date: 2026-01-09

Adds complete chat system with WebSocket support:
- chats: Main chat conversations
- chat_participants: Users/customers in chats  
- chat_messages: Individual messages
- chat_message_reads: Read receipts
- chat_attachments: Multiple file attachments
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '027_add_chat_tables'
down_revision = '026_add_faq_and_support_messages'
branch_labels = None
depends_on = None


def upgrade():
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_type', sa.Enum('user_customer', 'user_user', 'customer_customer', name='chattype'), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_preview', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chats_salon_id'), 'chats', ['salon_id'], unique=False)
    
    # Create chat_participants table
    op.create_table(
        'chat_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('participant_type', sa.Enum('user', 'customer', name='participanttype'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('unread_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_read_at', sa.DateTime(), nullable=True),
        sa.Column('last_read_message_id', sa.Integer(), nullable=True),
        sa.Column('is_muted', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_participants_chat_id'), 'chat_participants', ['chat_id'], unique=False)
    op.create_index(op.f('ix_chat_participants_user_id'), 'chat_participants', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_participants_customer_id'), 'chat_participants', ['customer_id'], unique=False)
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.Enum('user', 'customer', name='participanttype'), nullable=False),
        sa.Column('sender_user_id', sa.Integer(), nullable=True),
        sa.Column('sender_customer_id', sa.Integer(), nullable=True),
        sa.Column('message_type', sa.Enum('text', 'image', 'voice', 'system', name='messagetype'), nullable=False, default='text'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('media_url', sa.String(length=500), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('media_size', sa.Integer(), nullable=True),
        sa.Column('media_duration', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('reference_type', sa.Enum('appointment', 'product', 'pack', 'order', name='referencetype'), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('reference_data', sa.Text(), nullable=True),
        sa.Column('reply_to_message_id', sa.Integer(), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=True, default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_delivered', sa.Boolean(), nullable=True, default=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['sender_customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['reply_to_message_id'], ['chat_messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_chat_id'), 'chat_messages', ['chat_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_sender_user_id'), 'chat_messages', ['sender_user_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_sender_customer_id'), 'chat_messages', ['sender_customer_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    
    # Create chat_message_reads table
    op.create_table(
        'chat_message_reads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('reader_type', sa.Enum('user', 'customer', name='participanttype'), nullable=False),
        sa.Column('reader_user_id', sa.Integer(), nullable=True),
        sa.Column('reader_customer_id', sa.Integer(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reader_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reader_customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_message_reads_message_id'), 'chat_message_reads', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_message_reads_reader_user_id'), 'chat_message_reads', ['reader_user_id'], unique=False)
    op.create_index(op.f('ix_chat_message_reads_reader_customer_id'), 'chat_message_reads', ['reader_customer_id'], unique=False)
    
    # Create chat_attachments table
    op.create_table(
        'chat_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_attachments_message_id'), 'chat_attachments', ['message_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_chat_attachments_message_id'), table_name='chat_attachments')
    op.drop_table('chat_attachments')
    
    op.drop_index(op.f('ix_chat_message_reads_reader_customer_id'), table_name='chat_message_reads')
    op.drop_index(op.f('ix_chat_message_reads_reader_user_id'), table_name='chat_message_reads')
    op.drop_index(op.f('ix_chat_message_reads_message_id'), table_name='chat_message_reads')
    op.drop_table('chat_message_reads')
    
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_sender_customer_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_sender_user_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_chat_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    
    op.drop_index(op.f('ix_chat_participants_customer_id'), table_name='chat_participants')
    op.drop_index(op.f('ix_chat_participants_user_id'), table_name='chat_participants')
    op.drop_index(op.f('ix_chat_participants_chat_id'), table_name='chat_participants')
    op.drop_table('chat_participants')
    
    op.drop_index(op.f('ix_chats_salon_id'), table_name='chats')
    op.drop_table('chats')
    
    # Drop enums
    sa.Enum(name='chattype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='participanttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='messagetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='referencetype').drop(op.get_bind(), checkfirst=True)
