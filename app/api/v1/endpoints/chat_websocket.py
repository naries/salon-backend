"""
WebSocket Chat Endpoints

Real-time chat functionality via WebSocket connections.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging

from app.core.database import get_db
from app.core.chat_manager import chat_manager
from app.models.models import User, Customer
from app.models.chat_models import Chat, ChatParticipant, ChatMessage, ChatMessageRead
from app.schemas.chat_schemas import (
    WSMessageType, WSSendMessage, WSJoinChat, WSLeaveChat, 
    WSTyping, WSReadMessage, MessageTypeEnum
)
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Validate JWT token and return user"""
    from jose import JWTError, jwt
    from app.core.config import settings
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    return db.query(User).filter(User.email == email).first()


async def get_customer_from_token(token: str, db: Session) -> Optional[Customer]:
    """Validate JWT token and return customer"""
    from jose import JWTError, jwt
    from app.core.config import settings
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            return None
    except JWTError:
        return None
    
    return db.query(Customer).filter(Customer.phone == phone).first()


@router.websocket("/ws/chat/user")
async def websocket_chat_user(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for salon users (admins/staff).
    
    Connect: ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_JWT_TOKEN
    
    Message Types (Client → Server):
    - join_chat: Join a chat room
    - leave_chat: Leave a chat room
    - send_message: Send a message
    - typing: Send typing indicator
    - read_message: Mark message as read
    - ping: Keepalive ping
    
    Message Types (Server → Client):
    - connected: Connection confirmed
    - message: New message received
    - typing: Someone is typing
    - read_receipt: Message was read
    - user_joined: Someone joined the chat
    - user_left: Someone left the chat
    - error: Error occurred
    - pong: Response to ping
    """
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    if not user.salon_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect to chat manager
    await chat_manager.connect(
        websocket=websocket,
        participant_type="user",
        participant_id=user.id,
        salon_id=user.salon_id
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type")
            
            # Handle different message types
            if message_type == WSMessageType.JOIN_CHAT:
                await handle_join_chat(user.id, "user", message_data, db)
            
            elif message_type == WSMessageType.LEAVE_CHAT:
                await handle_leave_chat(user.id, "user", message_data)
            
            elif message_type == WSMessageType.SEND_MESSAGE:
                await handle_send_message(user.id, "user", user.salon_id, message_data, db)
            
            elif message_type == WSMessageType.TYPING:
                await handle_typing(user.id, "user", message_data)
            
            elif message_type == WSMessageType.READ_MESSAGE:
                await handle_read_message(user.id, "user", message_data, db)
            
            elif message_type == WSMessageType.PING:
                await chat_manager.send_to_connection(("user", user.id), {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await chat_manager.send_to_connection(("user", user.id), {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        await chat_manager.disconnect("user", user.id, "Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        await chat_manager.disconnect("user", user.id, f"Error: {str(e)}")


@router.websocket("/ws/chat/customer")
async def websocket_chat_customer(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for customers.
    
    Connect: ws://localhost:8000/api/v1/chat/ws/chat/customer?token=YOUR_JWT_TOKEN
    
    Same message types as user endpoint.
    """
    # Authenticate customer
    customer = await get_customer_from_token(token, db)
    if not customer:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Get salon_id from customer's first active chat, or use a default
    # Customers can chat with multiple salons, so we need to handle this dynamically
    first_chat = db.query(Chat).join(ChatParticipant).filter(
        ChatParticipant.customer_id == customer.id,
        ChatParticipant.participant_type == "customer",
        Chat.is_active == True
    ).first()
    
    salon_id = first_chat.salon_id if first_chat else None
    
    if not salon_id:
        # If no existing chats, we'll set salon_id when they join their first chat
        salon_id = 1  # Temporary default
    
    # Connect to chat manager
    await chat_manager.connect(
        websocket=websocket,
        participant_type="customer",
        participant_id=customer.id,
        salon_id=salon_id
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type")
            
            # Handle different message types
            if message_type == WSMessageType.JOIN_CHAT:
                await handle_join_chat(customer.id, "customer", message_data, db)
            
            elif message_type == WSMessageType.LEAVE_CHAT:
                await handle_leave_chat(customer.id, "customer", message_data)
            
            elif message_type == WSMessageType.SEND_MESSAGE:
                await handle_send_message(customer.id, "customer", salon_id, message_data, db)
            
            elif message_type == WSMessageType.TYPING:
                await handle_typing(customer.id, "customer", message_data)
            
            elif message_type == WSMessageType.READ_MESSAGE:
                await handle_read_message(customer.id, "customer", message_data, db)
            
            elif message_type == WSMessageType.PING:
                await chat_manager.send_to_connection(("customer", customer.id), {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await chat_manager.send_to_connection(("customer", customer.id), {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        await chat_manager.disconnect("customer", customer.id, "Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for customer {customer.id}: {e}")
        await chat_manager.disconnect("customer", customer.id, f"Error: {str(e)}")


# ==================== Message Handlers ====================

async def handle_join_chat(participant_id: int, participant_type: str, message_data: dict, db: Session):
    """Handle join_chat message"""
    chat_id = message_data.get("chat_id")
    if not chat_id:
        return
    
    # Verify participant is in this chat
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.participant_type == participant_type,
        getattr(ChatParticipant, f"{participant_type}_id") == participant_id
    ).first()
    
    if not participant:
        await chat_manager.send_to_connection((participant_type, participant_id), {
            "type": "error",
            "error": "You are not a participant in this chat"
        })
        return
    
    # Join the chat room
    await chat_manager.join_chat_room(chat_id, participant_type, participant_id)


async def handle_leave_chat(participant_id: int, participant_type: str, message_data: dict):
    """Handle leave_chat message"""
    chat_id = message_data.get("chat_id")
    if not chat_id:
        return
    
    await chat_manager.leave_chat_room(chat_id, participant_type, participant_id)


async def handle_send_message(
    participant_id: int, 
    participant_type: str, 
    salon_id: int,
    message_data: dict, 
    db: Session
):
    """Handle send_message - save to DB and broadcast"""
    chat_id = message_data.get("chat_id")
    content = message_data.get("content")
    message_type = message_data.get("message_type", "text")
    reply_to_message_id = message_data.get("reply_to_message_id")
    
    if not chat_id:
        return
    
    # Verify chat exists and participant is in it
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return
    
    # Create message in database
    message = ChatMessage(
        chat_id=chat_id,
        sender_type=participant_type,
        sender_user_id=participant_id if participant_type == "user" else None,
        sender_customer_id=participant_id if participant_type == "customer" else None,
        message_type=message_type,
        content=content,
        reply_to_message_id=reply_to_message_id,
        is_delivered=True,
        delivered_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Update chat's last message
    chat.last_message_at = message.created_at
    chat.last_message_preview = content[:100] if content else "[Media]"
    db.commit()
    
    # Update unread count for other participants
    participants = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.is_active == True
    ).all()
    
    for p in participants:
        # Skip sender
        if p.participant_type == participant_type:
            if (participant_type == "user" and p.user_id == participant_id) or \
               (participant_type == "customer" and p.customer_id == participant_id):
                continue
        
        # Increment unread count
        p.unread_count += 1
    
    db.commit()
    
    # Get sender info for broadcast
    if participant_type == "user":
        sender = db.query(User).filter(User.id == participant_id).first()
        sender_name = sender.email if sender else "Unknown"
    else:
        sender = db.query(Customer).filter(Customer.id == participant_id).first()
        sender_name = sender.phone if sender else "Unknown"
    
    # Broadcast message via WebSocket
    await chat_manager.send_message(
        chat_id=chat_id,
        message_data={
            "id": message.id,
            "chat_id": chat_id,
            "sender_type": participant_type,
            "sender_id": participant_id,
            "sender_name": sender_name,
            "message_type": message_type,
            "content": content,
            "reply_to_message_id": reply_to_message_id,
            "created_at": message.created_at.isoformat(),
            "is_delivered": True
        },
        sender_type=participant_type,
        sender_id=participant_id
    )


async def handle_typing(participant_id: int, participant_type: str, message_data: dict):
    """Handle typing indicator"""
    chat_id = message_data.get("chat_id")
    is_typing = message_data.get("is_typing", False)
    
    if not chat_id:
        return
    
    await chat_manager.send_typing_indicator(
        chat_id=chat_id,
        participant_type=participant_type,
        participant_id=participant_id,
        is_typing=is_typing
    )


async def handle_read_message(participant_id: int, participant_type: str, message_data: dict, db: Session):
    """Handle read message - mark as read and send receipt"""
    chat_id = message_data.get("chat_id")
    message_id = message_data.get("message_id")
    
    if not chat_id or not message_id:
        return
    
    # Check if already read
    existing_read = db.query(ChatMessageRead).filter(
        ChatMessageRead.message_id == message_id,
        ChatMessageRead.reader_type == participant_type,
        getattr(ChatMessageRead, f"reader_{participant_type}_id") == participant_id
    ).first()
    
    if not existing_read:
        # Create read receipt
        read_receipt = ChatMessageRead(
            message_id=message_id,
            reader_type=participant_type,
            reader_user_id=participant_id if participant_type == "user" else None,
            reader_customer_id=participant_id if participant_type == "customer" else None
        )
        db.add(read_receipt)
        
        # Update participant's unread count and last read
        participant = db.query(ChatParticipant).filter(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.participant_type == participant_type,
            getattr(ChatParticipant, f"{participant_type}_id") == participant_id
        ).first()
        
        if participant:
            participant.unread_count = max(0, participant.unread_count - 1)
            participant.last_read_at = datetime.utcnow()
            participant.last_read_message_id = message_id
        
        db.commit()
    
    # Send read receipt to other participants
    await chat_manager.send_read_receipt(
        chat_id=chat_id,
        message_id=message_id,
        reader_type=participant_type,
        reader_id=participant_id
    )
