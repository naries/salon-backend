"""
Chat Schemas

Pydantic models for chat API requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums matching database enums
class ChatTypeEnum(str, Enum):
    USER_CUSTOMER = "user_customer"
    USER_USER = "user_user"
    CUSTOMER_CUSTOMER = "customer_customer"


class MessageTypeEnum(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    SYSTEM = "system"


class ReferenceTypeEnum(str, Enum):
    APPOINTMENT = "appointment"
    PRODUCT = "product"
    PACK = "pack"
    ORDER = "order"


class ParticipantTypeEnum(str, Enum):
    USER = "user"
    CUSTOMER = "customer"


# ==================== Chat Schemas ====================

class ChatCreate(BaseModel):
    """Create a new chat conversation"""
    customer_id: Optional[int] = Field(None, description="Customer ID (required for user initiating)")
    user_id: Optional[int] = Field(None, description="User ID (required for customer initiating)")
    title: Optional[str] = Field(None, max_length=255, description="Optional chat title")
    initial_message: Optional[str] = Field(None, description="First message to send")


class ChatParticipantInfo(BaseModel):
    """Information about a chat participant"""
    participant_type: ParticipantTypeEnum
    participant_id: int
    joined_at: datetime
    is_active: bool
    unread_count: int = 0
    is_muted: bool = False
    last_read_at: Optional[datetime] = None
    
    # Participant details (populated from user/customer)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ChatListItem(BaseModel):
    """Chat item for list view"""
    id: int
    chat_type: ChatTypeEnum
    salon_id: int
    title: Optional[str] = None
    is_active: bool
    is_archived: bool
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    created_at: datetime
    
    # Participants info
    participants: List[ChatParticipantInfo] = []
    unread_count: int = 0  # For current user
    
    # Online status
    online_participants: List[int] = []
    
    class Config:
        from_attributes = True


class ChatDetail(BaseModel):
    """Detailed chat information"""
    id: int
    chat_type: ChatTypeEnum
    salon_id: int
    title: Optional[str] = None
    is_active: bool
    is_archived: bool
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Participants
    participants: List[ChatParticipantInfo] = []
    
    # Stats
    total_messages: int = 0
    unread_count: int = 0
    
    class Config:
        from_attributes = True


# ==================== Message Schemas ====================

class MessageReferenceCreate(BaseModel):
    """Reference to an entity (appointment, product, pack)"""
    reference_type: ReferenceTypeEnum
    reference_id: int


class MessageCreate(BaseModel):
    """Create a new message"""
    chat_id: int
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT
    content: Optional[str] = Field(None, description="Text content or caption")
    
    # Media
    media_url: Optional[str] = Field(None, max_length=500)
    media_type: Optional[str] = Field(None, max_length=50)
    media_duration: Optional[int] = Field(None, description="Duration in seconds for voice notes")
    
    # Reference
    reference: Optional[MessageReferenceCreate] = None
    
    # Reply
    reply_to_message_id: Optional[int] = None
    
    @validator('content')
    def validate_text_message(cls, v, values):
        """Ensure text messages have content"""
        if values.get('message_type') == MessageTypeEnum.TEXT and not v:
            raise ValueError('Text messages must have content')
        return v


class MessageEdit(BaseModel):
    """Edit an existing message"""
    content: str = Field(..., min_length=1)


class MessageAttachmentInfo(BaseModel):
    """Attachment information"""
    id: int
    file_url: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageReadReceipt(BaseModel):
    """Read receipt information"""
    reader_type: ParticipantTypeEnum
    reader_id: int
    read_at: datetime
    
    # Reader details
    reader_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class MessageReferenceInfo(BaseModel):
    """Information about referenced entity"""
    reference_type: ReferenceTypeEnum
    reference_id: int
    reference_data: Optional[dict] = None  # JSON data about the entity


class MessageResponse(BaseModel):
    """Message response with all details"""
    id: int
    chat_id: int
    
    # Sender
    sender_type: ParticipantTypeEnum
    sender_user_id: Optional[int] = None
    sender_customer_id: Optional[int] = None
    sender_name: Optional[str] = None  # Populated from user/customer
    sender_avatar: Optional[str] = None
    
    # Content
    message_type: MessageTypeEnum
    content: Optional[str] = None
    
    # Media
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    media_size: Optional[int] = None
    media_duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    
    # Reference
    reference_type: Optional[ReferenceTypeEnum] = None
    reference_id: Optional[int] = None
    reference_data: Optional[dict] = None
    
    # Reply
    reply_to_message_id: Optional[int] = None
    reply_to_message: Optional['MessageResponse'] = None  # Nested message
    
    # Status
    is_edited: bool = False
    is_deleted: bool = False
    is_delivered: bool = False
    delivered_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Read receipts
    read_receipts: List[MessageReadReceipt] = []
    
    # Attachments
    attachments: List[MessageAttachmentInfo] = []
    
    class Config:
        from_attributes = True


# Handle forward reference
MessageResponse.model_rebuild()


class MessageListResponse(BaseModel):
    """Paginated message list"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ==================== WebSocket Message Schemas ====================

class WSMessageType(str, Enum):
    """WebSocket message types"""
    # Client to Server
    JOIN_CHAT = "join_chat"
    LEAVE_CHAT = "leave_chat"
    SEND_MESSAGE = "send_message"
    TYPING = "typing"
    READ_MESSAGE = "read_message"
    PING = "ping"
    
    # Server to Client
    CONNECTED = "connected"
    MESSAGE = "message"
    TYPING_INDICATOR = "typing"
    READ_RECEIPT = "read_receipt"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    ERROR = "error"
    PONG = "pong"


class WSMessage(BaseModel):
    """Base WebSocket message"""
    type: str
    data: Optional[dict] = None
    timestamp: Optional[str] = None


class WSJoinChat(BaseModel):
    """Join a chat room"""
    type: str = WSMessageType.JOIN_CHAT
    chat_id: int


class WSLeaveChat(BaseModel):
    """Leave a chat room"""
    type: str = WSMessageType.LEAVE_CHAT
    chat_id: int


class WSSendMessage(BaseModel):
    """Send a message via WebSocket"""
    type: str = WSMessageType.SEND_MESSAGE
    chat_id: int
    content: Optional[str] = None
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT
    reply_to_message_id: Optional[int] = None


class WSTyping(BaseModel):
    """Typing indicator"""
    type: str = WSMessageType.TYPING
    chat_id: int
    is_typing: bool


class WSReadMessage(BaseModel):
    """Mark message as read"""
    type: str = WSMessageType.READ_MESSAGE
    chat_id: int
    message_id: int


# ==================== File Upload ====================

class FileUploadResponse(BaseModel):
    """Response after uploading a file"""
    file_url: str
    file_name: str
    file_type: str
    file_size: int
    thumbnail_url: Optional[str] = None


# ==================== Statistics ====================

class ChatStats(BaseModel):
    """Chat statistics"""
    total_chats: int
    active_chats: int
    archived_chats: int
    total_messages: int
    unread_messages: int
    online_users: int = 0
