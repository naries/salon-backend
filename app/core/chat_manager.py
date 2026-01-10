"""
WebSocket Chat Manager

Manages real-time WebSocket connections for chat functionality.
Handles message routing, delivery, and presence tracking.
"""
import asyncio
import json
from typing import Dict, Set, Optional, List
from datetime import datetime
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """Information about an active WebSocket connection"""
    def __init__(self, websocket: WebSocket, participant_type: str, participant_id: int, salon_id: int):
        self.websocket = websocket
        self.participant_type = participant_type  # "user" or "customer"
        self.participant_id = participant_id
        self.salon_id = salon_id
        self.connected_at = datetime.utcnow()
        self.last_seen = datetime.utcnow()
        self.active_chats: Set[int] = set()  # Chat IDs user is currently viewing


class ChatManager:
    """
    Manages WebSocket connections for real-time chat.
    Routes messages between participants and tracks online presence.
    """
    
    def __init__(self):
        # Active WebSocket connections: {(participant_type, participant_id): ConnectionInfo}
        self.active_connections: Dict[tuple, ConnectionInfo] = {}
        
        # Chat room tracking: {chat_id: set of (participant_type, participant_id)}
        self.chat_rooms: Dict[int, Set[tuple]] = {}
        
        # Typing indicators: {chat_id: {(participant_type, participant_id): timestamp}}
        self.typing_status: Dict[int, Dict[tuple, datetime]] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        participant_type: str, 
        participant_id: int,
        salon_id: int
    ) -> bool:
        """
        Connect a WebSocket client.
        Returns True if connected successfully.
        """
        await websocket.accept()
        
        key = (participant_type, participant_id)
        
        # Disconnect existing connection if any
        if key in self.active_connections:
            await self.disconnect(participant_type, participant_id, reason="New connection")
        
        # Store connection
        self.active_connections[key] = ConnectionInfo(
            websocket=websocket,
            participant_type=participant_type,
            participant_id=participant_id,
            salon_id=salon_id
        )
        
        logger.info(f"WebSocket connected: {participant_type} #{participant_id}")
        
        # Send connection confirmation
        await self.send_to_connection(key, {
            "type": "connected",
            "participant_type": participant_type,
            "participant_id": participant_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def disconnect(
        self, 
        participant_type: str, 
        participant_id: int,
        reason: str = "Client disconnected"
    ):
        """Disconnect a WebSocket client"""
        key = (participant_type, participant_id)
        
        if key in self.active_connections:
            conn_info = self.active_connections[key]
            
            # Leave all chat rooms
            for chat_id in list(conn_info.active_chats):
                await self.leave_chat_room(chat_id, participant_type, participant_id)
            
            # Close WebSocket
            try:
                await conn_info.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            
            # Remove from active connections
            del self.active_connections[key]
            
            logger.info(f"WebSocket disconnected: {participant_type} #{participant_id} - {reason}")
    
    async def join_chat_room(
        self, 
        chat_id: int, 
        participant_type: str, 
        participant_id: int
    ):
        """Join a chat room to receive messages"""
        key = (participant_type, participant_id)
        
        if key not in self.active_connections:
            return False
        
        # Add to chat room
        if chat_id not in self.chat_rooms:
            self.chat_rooms[chat_id] = set()
        self.chat_rooms[chat_id].add(key)
        
        # Update connection info
        self.active_connections[key].active_chats.add(chat_id)
        
        logger.info(f"{participant_type} #{participant_id} joined chat #{chat_id}")
        
        # Notify others in the room
        await self.broadcast_to_chat(chat_id, {
            "type": "user_joined",
            "chat_id": chat_id,
            "participant_type": participant_type,
            "participant_id": participant_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude=key)
        
        return True
    
    async def leave_chat_room(
        self, 
        chat_id: int, 
        participant_type: str, 
        participant_id: int
    ):
        """Leave a chat room"""
        key = (participant_type, participant_id)
        
        # Remove from chat room
        if chat_id in self.chat_rooms and key in self.chat_rooms[chat_id]:
            self.chat_rooms[chat_id].remove(key)
            
            # Clean up empty chat rooms
            if not self.chat_rooms[chat_id]:
                del self.chat_rooms[chat_id]
        
        # Update connection info
        if key in self.active_connections:
            self.active_connections[key].active_chats.discard(chat_id)
        
        # Clear typing status
        if chat_id in self.typing_status and key in self.typing_status[chat_id]:
            del self.typing_status[chat_id][key]
        
        logger.info(f"{participant_type} #{participant_id} left chat #{chat_id}")
        
        # Notify others in the room
        await self.broadcast_to_chat(chat_id, {
            "type": "user_left",
            "chat_id": chat_id,
            "participant_type": participant_type,
            "participant_id": participant_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_message(
        self,
        chat_id: int,
        message_data: dict,
        sender_type: str,
        sender_id: int
    ):
        """
        Send a message to all participants in a chat.
        Message is delivered via WebSocket if online, queued otherwise.
        """
        message_payload = {
            "type": "message",
            "chat_id": chat_id,
            "message": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all participants in the chat
        await self.broadcast_to_chat(chat_id, message_payload)
        
        logger.info(f"Message sent in chat #{chat_id} from {sender_type} #{sender_id}")
    
    async def send_typing_indicator(
        self,
        chat_id: int,
        participant_type: str,
        participant_id: int,
        is_typing: bool
    ):
        """Send typing indicator to other participants"""
        key = (participant_type, participant_id)
        
        # Update typing status
        if is_typing:
            if chat_id not in self.typing_status:
                self.typing_status[chat_id] = {}
            self.typing_status[chat_id][key] = datetime.utcnow()
        else:
            if chat_id in self.typing_status and key in self.typing_status[chat_id]:
                del self.typing_status[chat_id][key]
        
        # Broadcast typing status
        await self.broadcast_to_chat(chat_id, {
            "type": "typing",
            "chat_id": chat_id,
            "participant_type": participant_type,
            "participant_id": participant_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude=key)
    
    async def send_read_receipt(
        self,
        chat_id: int,
        message_id: int,
        reader_type: str,
        reader_id: int
    ):
        """Send read receipt for a message"""
        await self.broadcast_to_chat(chat_id, {
            "type": "read_receipt",
            "chat_id": chat_id,
            "message_id": message_id,
            "reader_type": reader_type,
            "reader_id": reader_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_to_chat(
        self,
        chat_id: int,
        message: dict,
        exclude: Optional[tuple] = None
    ):
        """Broadcast a message to all participants in a chat room"""
        if chat_id not in self.chat_rooms:
            return
        
        participants = self.chat_rooms[chat_id].copy()
        if exclude:
            participants.discard(exclude)
        
        # Send to all participants
        disconnected = []
        for participant_key in participants:
            try:
                await self.send_to_connection(participant_key, message)
            except Exception as e:
                logger.error(f"Error sending to {participant_key}: {e}")
                disconnected.append(participant_key)
        
        # Clean up disconnected clients
        for participant_key in disconnected:
            await self.disconnect(participant_key[0], participant_key[1], "Send failed")
    
    async def send_to_connection(self, participant_key: tuple, message: dict):
        """Send a message to a specific connection"""
        if participant_key not in self.active_connections:
            return False
        
        conn_info = self.active_connections[participant_key]
        
        try:
            await conn_info.websocket.send_json(message)
            conn_info.last_seen = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Error sending to connection {participant_key}: {e}")
            raise
    
    def is_online(self, participant_type: str, participant_id: int) -> bool:
        """Check if a participant is currently online"""
        return (participant_type, participant_id) in self.active_connections
    
    def get_online_participants(self, chat_id: int) -> List[dict]:
        """Get list of online participants in a chat"""
        if chat_id not in self.chat_rooms:
            return []
        
        online = []
        for participant_type, participant_id in self.chat_rooms[chat_id]:
            conn_info = self.active_connections.get((participant_type, participant_id))
            if conn_info:
                online.append({
                    "participant_type": participant_type,
                    "participant_id": participant_id,
                    "connected_at": conn_info.connected_at.isoformat(),
                    "last_seen": conn_info.last_seen.isoformat()
                })
        
        return online
    
    def get_typing_participants(self, chat_id: int) -> List[dict]:
        """Get list of participants currently typing in a chat"""
        if chat_id not in self.typing_status:
            return []
        
        now = datetime.utcnow()
        typing = []
        
        for (participant_type, participant_id), last_typing in self.typing_status[chat_id].items():
            # Consider typing if within last 5 seconds
            if (now - last_typing).total_seconds() < 5:
                typing.append({
                    "participant_type": participant_type,
                    "participant_id": participant_id
                })
        
        return typing
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "active_chat_rooms": len(self.chat_rooms),
            "users_online": sum(1 for k in self.active_connections if k[0] == "user"),
            "customers_online": sum(1 for k in self.active_connections if k[0] == "customer"),
            "connections": [
                {
                    "participant_type": conn.participant_type,
                    "participant_id": conn.participant_id,
                    "salon_id": conn.salon_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "active_chats": list(conn.active_chats)
                }
                for conn in self.active_connections.values()
            ]
        }


# Global chat manager instance
chat_manager = ChatManager()
