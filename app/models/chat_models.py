"""
Chat System Models

Provides real-time messaging between users and salons/customers.
Supports multiple conversations, media attachments, and message references.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class ChatType(str, enum.Enum):
    """Type of chat conversation"""
    USER_CUSTOMER = "user_customer"  # Salon staff chatting with customer
    USER_USER = "user_user"  # Staff to staff (future)
    CUSTOMER_CUSTOMER = "customer_customer"  # Customer to customer (future)


class MessageType(str, enum.Enum):
    """Type of message content"""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    SYSTEM = "system"  # System messages like "User joined"


class ReferenceType(str, enum.Enum):
    """Types of entities that can be referenced in messages"""
    APPOINTMENT = "appointment"
    PRODUCT = "product"
    PACK = "pack"
    ORDER = "order"


class ParticipantType(str, enum.Enum):
    """Type of chat participant"""
    USER = "user"  # Salon admin/staff
    CUSTOMER = "customer"


class Chat(Base):
    """
    Chat conversation between parties.
    Represents a thread of messages between users and customers.
    """
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_type = Column(SQLEnum(ChatType), nullable=False, default=ChatType.USER_CUSTOMER)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False, index=True)
    
    # Chat metadata
    title = Column(String(255), nullable=True)  # Optional chat title
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Last message info (for quick display in chat list)
    last_message_at = Column(DateTime, nullable=True)
    last_message_preview = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="chats")
    participants = relationship("ChatParticipant", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatParticipant(Base):
    """
    Participants in a chat conversation.
    Links users or customers to specific chats.
    """
    __tablename__ = "chat_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Participant identification
    participant_type = Column(SQLEnum(ParticipantType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # If salon staff
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)  # If customer
    
    # Participant metadata
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Unread count for this participant
    unread_count = Column(Integer, default=0)
    last_read_at = Column(DateTime, nullable=True)
    last_read_message_id = Column(Integer, nullable=True)
    
    # Notification preferences
    is_muted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="participants")
    user = relationship("User", backref="chat_participations")
    customer = relationship("Customer", backref="chat_participations")
    
    # Check constraint to ensure either user_id or customer_id is set
    __table_args__ = (
        # Ensure participant_type matches the ID that's set
    )


class ChatMessage(Base):
    """
    Individual messages within a chat.
    Supports text, images, voice notes, and entity references.
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Sender identification
    sender_type = Column(SQLEnum(ParticipantType), nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sender_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    
    # Message content
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    content = Column(Text, nullable=True)  # Text content or caption
    
    # Media attachments
    media_url = Column(String(500), nullable=True)  # URL to image/voice file
    media_type = Column(String(50), nullable=True)  # MIME type
    media_size = Column(Integer, nullable=True)  # File size in bytes
    media_duration = Column(Integer, nullable=True)  # For voice notes (seconds)
    thumbnail_url = Column(String(500), nullable=True)  # For images/videos
    
    # Entity references (appointment, product, pack)
    reference_type = Column(SQLEnum(ReferenceType), nullable=True)
    reference_id = Column(Integer, nullable=True)
    reference_data = Column(Text, nullable=True)  # JSON data about referenced entity
    
    # Reply to another message
    reply_to_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    
    # Message status
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Delivery tracking
    is_delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender_user = relationship("User", foreign_keys=[sender_user_id], backref="sent_messages")
    sender_customer = relationship("Customer", foreign_keys=[sender_customer_id], backref="sent_messages")
    reply_to = relationship("ChatMessage", remote_side=[id], backref="replies")
    read_receipts = relationship("ChatMessageRead", back_populates="message", cascade="all, delete-orphan")


class ChatMessageRead(Base):
    """
    Tracks read receipts for messages.
    Shows who has read which messages.
    """
    __tablename__ = "chat_message_reads"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Reader identification
    reader_type = Column(SQLEnum(ParticipantType), nullable=False)
    reader_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reader_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    
    # Read timestamp
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("ChatMessage", back_populates="read_receipts")
    reader_user = relationship("User", backref="message_reads")
    reader_customer = relationship("Customer", backref="message_reads")


class ChatAttachment(Base):
    """
    Additional attachments for messages (multiple files per message).
    Extends beyond the single media_url in ChatMessage.
    """
    __tablename__ = "chat_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File information
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)  # MIME type
    file_size = Column(Integer, nullable=True)
    
    # For media files
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)  # For audio/video
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("ChatMessage", backref="attachments")
