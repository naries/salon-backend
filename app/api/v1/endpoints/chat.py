"""
Chat REST API Endpoints

HTTP endpoints for chat management (create, list, history, etc.).
Use these alongside WebSocket for complete chat functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, func
from typing import List, Optional
from datetime import datetime
import json

from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_customer
from app.core.chat_manager import chat_manager
from app.models.models import User, Customer, Salon
from app.models.chat_models import (
    Chat, ChatParticipant, ChatMessage, ChatMessageRead, ChatAttachment,
    ParticipantType, MessageType, ChatType
)
from app.schemas.chat_schemas import (
    ChatCreate, ChatListItem, ChatDetail, ChatParticipantInfo,
    MessageCreate, MessageResponse, MessageListResponse, MessageEdit,
    FileUploadResponse, ChatStats
)

router = APIRouter()


# ==================== Chat Management ====================

@router.post("/chats", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new chat conversation (Admin initiates with customer).
    Admin must specify customer_id to chat with.
    """
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be associated with a salon"
        )
    
    if not chat_data.customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_id is required"
        )
    
    # Check if customer exists
    customer = db.query(Customer).filter(Customer.id == chat_data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Check if chat already exists between this user and customer
    existing_chat = db.query(Chat).join(ChatParticipant).filter(
        Chat.salon_id == current_user.salon_id,
        Chat.is_active == True,
        ChatParticipant.chat_id == Chat.id,
        or_(
            and_(ChatParticipant.user_id == current_user.id, ChatParticipant.participant_type == ParticipantType.USER),
            and_(ChatParticipant.customer_id == chat_data.customer_id, ChatParticipant.participant_type == ParticipantType.CUSTOMER)
        )
    ).group_by(Chat.id).having(func.count(ChatParticipant.id) >= 2).first()
    
    if existing_chat:
        # Return existing chat
        return get_chat_detail(existing_chat, current_user.id, "user", db)
    
    # Create new chat
    chat = Chat(
        chat_type=ChatType.USER_CUSTOMER,
        salon_id=current_user.salon_id,
        title=chat_data.title
    )
    db.add(chat)
    db.flush()
    
    # Add participants
    user_participant = ChatParticipant(
        chat_id=chat.id,
        participant_type=ParticipantType.USER,
        user_id=current_user.id
    )
    customer_participant = ChatParticipant(
        chat_id=chat.id,
        participant_type=ParticipantType.CUSTOMER,
        customer_id=chat_data.customer_id
    )
    
    db.add(user_participant)
    db.add(customer_participant)
    db.commit()
    db.refresh(chat)
    
    # Send initial message if provided
    if chat_data.initial_message:
        message = ChatMessage(
            chat_id=chat.id,
            sender_type=ParticipantType.USER,
            sender_user_id=current_user.id,
            message_type=MessageType.TEXT,
            content=chat_data.initial_message,
            is_delivered=True,
            delivered_at=datetime.utcnow()
        )
        db.add(message)
        
        chat.last_message_at = message.created_at
        chat.last_message_preview = chat_data.initial_message[:100]
        customer_participant.unread_count = 1
        
        db.commit()
    
    return get_chat_detail(chat, current_user.id, "user", db)


@router.post("/chats/customer", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
async def create_chat_customer(
    chat_data: ChatCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Create a new chat conversation (Customer initiates with salon).
    Customer must specify salon_id. Optionally provide user_id for specific user.
    """
    if not chat_data.salon_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="salon_id is required to start a chat"
        )
    
    # Verify salon exists
    salon = db.query(Salon).filter(Salon.id == chat_data.salon_id).first()
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    
    salon_id = chat_data.salon_id
    
    # If user_id provided, verify user belongs to this salon
    user = None
    if chat_data.user_id:
        user = db.query(User).filter(
            User.id == chat_data.user_id,
            User.salon_id == salon_id
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or not associated with this salon"
            )
    
    # Check if chat already exists
    existing_chat = db.query(Chat).join(ChatParticipant).filter(
        Chat.salon_id == salon_id,
        Chat.is_active == True,
        ChatParticipant.chat_id == Chat.id,
        ChatParticipant.customer_id == current_customer.id,
        ChatParticipant.participant_type == ParticipantType.CUSTOMER
    ).first()
    
    if existing_chat:
        return get_chat_detail(existing_chat, current_customer.id, "customer", db)
    
    # Create new chat
    chat = Chat(
        chat_type=ChatType.USER_CUSTOMER,
        salon_id=salon_id,
        title=chat_data.title
    )
    db.add(chat)
    db.flush()
    
    # Add participants
    # Add user participant only if specific user was requested
    if user:
        user_participant = ChatParticipant(
            chat_id=chat.id,
            participant_type=ParticipantType.USER,
            user_id=user.id
        )
        db.add(user_participant)
    
    customer_participant = ChatParticipant(
        chat_id=chat.id,
        participant_type=ParticipantType.CUSTOMER,
        customer_id=current_customer.id
    )
    db.add(customer_participant)
    db.commit()
    db.refresh(chat)
    
    # Send initial message if provided
    if chat_data.initial_message:
        message = ChatMessage(
            chat_id=chat.id,
            sender_type=ParticipantType.CUSTOMER,
            sender_customer_id=current_customer.id,
            message_type=MessageType.TEXT,
            content=chat_data.initial_message,
            is_delivered=True,
            delivered_at=datetime.utcnow()
        )
        db.add(message)
        
        chat.last_message_at = message.created_at
        chat.last_message_preview = chat_data.initial_message[:100]
        user_participant.unread_count = 1
        
        db.commit()
    
    return get_chat_detail(chat, current_customer.id, "customer", db)


@router.get("/chats", response_model=List[ChatListItem])
async def list_chats(
    is_archived: bool = Query(False, description="Show archived chats"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """List all chats for the current user"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be associated with a salon"
        )
    
    # Get chats where user is a participant
    chats = db.query(Chat).join(ChatParticipant).filter(
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.participant_type == ParticipantType.USER,
        Chat.is_archived == is_archived,
        Chat.is_active == True
    ).order_by(desc(Chat.last_message_at)).all()
    
    return [format_chat_list_item(chat, current_user.id, "user", db) for chat in chats]


@router.get("/chats/customer", response_model=List[ChatListItem])
async def list_chats_customer(
    is_archived: bool = Query(False, description="Show archived chats"),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """List all chats for the current customer"""
    chats = db.query(Chat).join(ChatParticipant).filter(
        ChatParticipant.customer_id == current_customer.id,
        ChatParticipant.participant_type == ParticipantType.CUSTOMER,
        Chat.is_archived == is_archived,
        Chat.is_active == True
    ).order_by(desc(Chat.last_message_at)).all()
    
    return [format_chat_list_item(chat, current_customer.id, "customer", db) for chat in chats]


@router.get("/chats/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get detailed chat information"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Verify user is participant
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.participant_type == ParticipantType.USER
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat"
        )
    
    return get_chat_detail(chat, current_user.id, "user", db)


# ==================== Message Management ====================

@router.get("/chats/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    before_message_id: Optional[int] = Query(None, description="Get messages before this ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get paginated message history for a chat.
    Returns messages in reverse chronological order (newest first).
    """
    # Verify user is participant
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat"
        )
    
    # Build query
    query = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.is_deleted == False
    )
    
    if before_message_id:
        query = query.filter(ChatMessage.id < before_message_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated messages
    offset = (page - 1) * page_size
    messages = query.order_by(desc(ChatMessage.created_at)).offset(offset).limit(page_size).all()
    
    # Format messages
    formatted_messages = [format_message_response(msg, db) for msg in messages]
    
    return MessageListResponse(
        messages=formatted_messages,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(messages)) < total
    )


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message_http(
    chat_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Send a message via HTTP (alternative to WebSocket).
    Use WebSocket for real-time chat, HTTP for initial messages or offline support.
    """
    if message_data.chat_id != chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id mismatch"
        )
    
    # Verify user is participant
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat"
        )
    
    # Create message
    message = ChatMessage(
        chat_id=chat_id,
        sender_type=ParticipantType.USER,
        sender_user_id=current_user.id,
        message_type=message_data.message_type,
        content=message_data.content,
        media_url=message_data.media_url,
        media_type=message_data.media_type,
        media_duration=message_data.media_duration,
        reply_to_message_id=message_data.reply_to_message_id,
        reference_type=message_data.reference.reference_type if message_data.reference else None,
        reference_id=message_data.reference.reference_id if message_data.reference else None,
        is_delivered=True,
        delivered_at=datetime.utcnow()
    )
    
    db.add(message)
    db.flush()
    
    # Update chat
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    chat.last_message_at = message.created_at
    chat.last_message_preview = message_data.content[:100] if message_data.content else "[Media]"
    
    # Update unread count for other participants
    db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id != current_user.id
    ).update({ChatParticipant.unread_count: ChatParticipant.unread_count + 1})
    
    db.commit()
    db.refresh(message)
    
    # Broadcast via WebSocket if participants are online
    if chat_manager.is_online("user", current_user.id):
        await chat_manager.send_message(
            chat_id=chat_id,
            message_data=format_message_response(message, db).__dict__,
            sender_type="user",
            sender_id=current_user.id
        )
    
    return format_message_response(message, db)


@router.put("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: int,
    edit_data: MessageEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Edit a message (text only, within 15 minutes)"""
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify sender
    if message.sender_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages"
        )
    
    # Check time limit (15 minutes)
    if (datetime.utcnow() - message.created_at).total_seconds() > 900:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message can only be edited within 15 minutes"
        )
    
    # Update message
    message.content = edit_data.content
    message.is_edited = True
    db.commit()
    db.refresh(message)
    
    return format_message_response(message, db)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Soft delete a message"""
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify sender
    if message.sender_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages"
        )
    
    # Soft delete
    message.is_deleted = True
    message.deleted_at = datetime.utcnow()
    message.content = "[Message deleted]"
    db.commit()
    
    return {"message": "Message deleted successfully"}


# ==================== File Upload ====================

@router.post("/upload", response_model=FileUploadResponse)
async def upload_chat_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload a file (image, voice note, etc.) for chat.
    Returns URL to use in message.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "audio/mpeg", "audio/ogg", "audio/wav"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed"
        )
    
    # Validate file size (10MB max)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )
    
    # Upload to storage (implement this based on your storage solution)
    # file_url = await upload_file_to_storage(file_content, file.filename, file.content_type)
    
    # For now, return a placeholder
    file_url = f"/uploads/chat/{datetime.utcnow().timestamp()}_{file.filename}"
    
    return FileUploadResponse(
        file_url=file_url,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=len(file_content)
    )


# ==================== Statistics ====================

@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get chat statistics for current user"""
    if not current_user.salon_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be associated with a salon"
        )
    
    # Get user's chats
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.participant_type == ParticipantType.USER
    ).all()
    
    chat_ids = [p.chat_id for p in participant]
    
    total_chats = len(chat_ids)
    active_chats = db.query(Chat).filter(
        Chat.id.in_(chat_ids),
        Chat.is_active == True,
        Chat.is_archived == False
    ).count()
    
    archived_chats = db.query(Chat).filter(
        Chat.id.in_(chat_ids),
        Chat.is_archived == True
    ).count()
    
    total_messages = db.query(ChatMessage).filter(
        ChatMessage.chat_id.in_(chat_ids)
    ).count()
    
    unread_messages = sum(p.unread_count for p in participant)
    
    # Online users from chat manager
    stats = chat_manager.get_stats()
    
    return ChatStats(
        total_chats=total_chats,
        active_chats=active_chats,
        archived_chats=archived_chats,
        total_messages=total_messages,
        unread_messages=unread_messages,
        online_users=stats['users_online']
    )


# ==================== Helper Functions ====================

def get_chat_detail(chat: Chat, participant_id: int, participant_type: str, db: Session) -> ChatDetail:
    """Format chat detail response"""
    # Get participants
    participants = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat.id
    ).all()
    
    # Get current user's participant record for unread count
    current_participant = next(
        (p for p in participants if getattr(p, f"{participant_type}_id") == participant_id),
        None
    )
    
    # Format participants
    participant_infos = []
    for p in participants:
        if p.participant_type == ParticipantType.USER and p.user:
            participant_infos.append(ChatParticipantInfo(
                participant_type=p.participant_type,
                participant_id=p.user_id,
                joined_at=p.joined_at,
                is_active=p.is_active,
                unread_count=p.unread_count,
                is_muted=p.is_muted,
                last_read_at=p.last_read_at,
                name=p.user.email,
                email=p.user.email
            ))
        elif p.participant_type == ParticipantType.CUSTOMER and p.customer:
            participant_infos.append(ChatParticipantInfo(
                participant_type=p.participant_type,
                participant_id=p.customer_id,
                joined_at=p.joined_at,
                is_active=p.is_active,
                unread_count=p.unread_count,
                is_muted=p.is_muted,
                last_read_at=p.last_read_at,
                phone=p.customer.phone_number
            ))
    
    # Get message count
    total_messages = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat.id,
        ChatMessage.is_deleted == False
    ).count()
    
    return ChatDetail(
        id=chat.id,
        chat_type=chat.chat_type,
        salon_id=chat.salon_id,
        title=chat.title,
        is_active=chat.is_active,
        is_archived=chat.is_archived,
        last_message_at=chat.last_message_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        participants=participant_infos,
        total_messages=total_messages,
        unread_count=current_participant.unread_count if current_participant else 0
    )


def format_chat_list_item(chat: Chat, participant_id: int, participant_type: str, db: Session) -> ChatListItem:
    """Format chat list item"""
    # Get participants
    participants = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat.id
    ).all()
    
    current_participant = next(
        (p for p in participants if getattr(p, f"{participant_type}_id") == participant_id),
        None
    )
    
    # Format participants
    participant_infos = []
    for p in participants:
        if p.participant_type == ParticipantType.USER and p.user:
            participant_infos.append(ChatParticipantInfo(
                participant_type=p.participant_type,
                participant_id=p.user_id,
                joined_at=p.joined_at,
                is_active=p.is_active,
                unread_count=p.unread_count,
                name=p.user.email,
                email=p.user.email
            ))
        elif p.participant_type == ParticipantType.CUSTOMER and p.customer:
            participant_infos.append(ChatParticipantInfo(
                participant_type=p.participant_type,
                participant_id=p.customer_id,
                joined_at=p.joined_at,
                is_active=p.is_active,
                unread_count=p.unread_count,
                phone=p.customer.phone_number
            ))
    
    # Get online participants
    online = chat_manager.get_online_participants(chat.id)
    online_ids = [p['participant_id'] for p in online]
    
    return ChatListItem(
        id=chat.id,
        chat_type=chat.chat_type,
        salon_id=chat.salon_id,
        title=chat.title,
        is_active=chat.is_active,
        is_archived=chat.is_archived,
        last_message_at=chat.last_message_at,
        last_message_preview=chat.last_message_preview,
        created_at=chat.created_at,
        participants=participant_infos,
        unread_count=current_participant.unread_count if current_participant else 0,
        online_participants=online_ids
    )


def format_message_response(message: ChatMessage, db: Session) -> MessageResponse:
    """Format message response"""
    # Get sender info
    sender_name = None
    sender_avatar = None
    
    if message.sender_type == ParticipantType.USER and message.sender_user:
        sender_name = message.sender_user.email
    elif message.sender_type == ParticipantType.CUSTOMER and message.sender_customer:
        sender_name = message.sender_customer.phone_number
    
    # Get read receipts
    read_receipts = db.query(ChatMessageRead).filter(
        ChatMessageRead.message_id == message.id
    ).all()
    
    # Parse reference data
    reference_data = None
    if message.reference_data:
        try:
            reference_data = json.loads(message.reference_data)
        except:
            pass
    
    return MessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        sender_type=message.sender_type,
        sender_user_id=message.sender_user_id,
        sender_customer_id=message.sender_customer_id,
        sender_name=sender_name,
        sender_avatar=sender_avatar,
        message_type=message.message_type,
        content=message.content,
        media_url=message.media_url,
        media_type=message.media_type,
        media_size=message.media_size,
        media_duration=message.media_duration,
        thumbnail_url=message.thumbnail_url,
        reference_type=message.reference_type,
        reference_id=message.reference_id,
        reference_data=reference_data,
        reply_to_message_id=message.reply_to_message_id,
        is_edited=message.is_edited,
        is_deleted=message.is_deleted,
        is_delivered=message.is_delivered,
        delivered_at=message.delivered_at,
        created_at=message.created_at,
        updated_at=message.updated_at,
        read_receipts=[
            MessageReadReceipt(
                reader_type=r.reader_type,
                reader_id=r.reader_user_id if r.reader_type == ParticipantType.USER else r.reader_customer_id,
                read_at=r.read_at
            )
            for r in read_receipts
        ]
    )
