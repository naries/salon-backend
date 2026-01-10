
# WebSocket Chat System - Frontend Integration Guide

## Overview

This guide provides complete details for integrating the WebSocket-based chat system into your frontend application. The chat system supports:

- Real-time messaging via WebSocket
- Multiple concurrent conversations
- Message types: text, images, voice notes
- Entity references: appointments, products, packs
- Read receipts and typing indicators
- Online presence tracking

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Connection Details](#connection-details)
3. [REST API Endpoints](#rest-api-endpoints)
4. [WebSocket Protocol](#websocket-protocol)
5. [Implementation Examples](#implementation-examples)
6. [Complete React Integration](#complete-react-integration)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Quick Start

### 1. WebSocket Connection URLs

**For Salon Admins/Staff:**
```
ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_JWT_TOKEN
```

**For Customers:**
```
ws://localhost:8000/api/v1/chat/ws/chat/customer?token=YOUR_JWT_TOKEN
```

### 2. Basic Connection (JavaScript)

```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/chat/user?token=${token}`);

ws.onopen = () => {
    console.log('Connected to chat');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected from chat');
};
```

---

## Connection Details

### Authentication

Authentication is done via JWT token in the WebSocket URL query parameter.

**Token Sources:**
- Admin/Staff: Login via `/api/v1/auth/login`
- Customer: Login via `/api/v1/customer-auth/login`

**Token Format:**
```
ws://YOUR_API_URL/api/v1/chat/ws/chat/user?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Connection Lifecycle

1. **Connect**: Open WebSocket connection with token
2. **Receive "connected" event**: Server confirms connection
3. **Join chat rooms**: Send `join_chat` for each conversation
4. **Send/Receive messages**: Real-time bidirectional communication
5. **Leave chat rooms**: Send `leave_chat` when navigating away
6. **Disconnect**: Close connection when done

---

## REST API Endpoints

Use REST API for:
- Creating chats
- Fetching chat history
- Uploading files
- Getting chat list

### Create Chat

**Admin initiating chat with customer:**
```http
POST /api/v1/chat/chats
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "customer_id": 123,
  "title": "Support Chat",
  "initial_message": "Hi, how can I help you?"
}
```

**Customer initiating chat with salon:**
```http
POST /api/v1/chat/chats/customer
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "user_id": 456,
  "title": "Booking Inquiry",
  "initial_message": "I'd like to book an appointment"
}
```

**Response:**
```json
{
  "id": 1,
  "chat_type": "user_customer",
  "salon_id": 10,
  "title": "Support Chat",
  "is_active": true,
  "is_archived": false,
  "last_message_at": "2026-01-09T10:30:00",
  "created_at": "2026-01-09T10:30:00",
  "updated_at": "2026-01-09T10:30:00",
  "participants": [
    {
      "participant_type": "user",
      "participant_id": 456,
      "joined_at": "2026-01-09T10:30:00",
      "is_active": true,
      "unread_count": 0,
      "name": "admin@salon.com",
      "email": "admin@salon.com"
    },
    {
      "participant_type": "customer",
      "participant_id": 123,
      "joined_at": "2026-01-09T10:30:00",
      "is_active": true,
      "unread_count": 1,
      "phone": "+1234567890"
    }
  ],
  "total_messages": 1,
  "unread_count": 0
}
```

### List Chats

**Admin:**
```http
GET /api/v1/chat/chats?is_archived=false
Authorization: Bearer YOUR_JWT_TOKEN
```

**Customer:**
```http
GET /api/v1/chat/chats/customer?is_archived=false
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response:**
```json
[
  {
    "id": 1,
    "chat_type": "user_customer",
    "salon_id": 10,
    "title": "Support Chat",
    "is_active": true,
    "is_archived": false,
    "last_message_at": "2026-01-09T10:30:00",
    "last_message_preview": "Hi, how can I help you?",
    "created_at": "2026-01-09T10:30:00",
    "participants": [...],
    "unread_count": 3,
    "online_participants": [456]
  }
]
```

### Get Chat Messages

```http
GET /api/v1/chat/chats/1/messages?page=1&page_size=50
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response:**
```json
{
  "messages": [
    {
      "id": 101,
      "chat_id": 1,
      "sender_type": "user",
      "sender_user_id": 456,
      "sender_name": "admin@salon.com",
      "message_type": "text",
      "content": "Hi, how can I help you?",
      "created_at": "2026-01-09T10:30:00",
      "is_edited": false,
      "is_deleted": false,
      "read_receipts": [
        {
          "reader_type": "customer",
          "reader_id": 123,
          "read_at": "2026-01-09T10:31:00"
        }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "has_more": false
}
```

### Upload File

```http
POST /api/v1/chat/upload
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

file: [binary file data]
```

**Response:**
```json
{
  "file_url": "/uploads/chat/1736424600.123_image.jpg",
  "file_name": "image.jpg",
  "file_type": "image/jpeg",
  "file_size": 524288,
  "thumbnail_url": "/uploads/chat/1736424600.123_image_thumb.jpg"
}
```

---

## WebSocket Protocol

### Message Types

#### Client → Server

| Type | Purpose | Required Fields |
|------|---------|----------------|
| `join_chat` | Join a chat room | `chat_id` |
| `leave_chat` | Leave a chat room | `chat_id` |
| `send_message` | Send a message | `chat_id`, `content` or `media_url` |
| `typing` | Send typing indicator | `chat_id`, `is_typing` |
| `read_message` | Mark message as read | `chat_id`, `message_id` |
| `ping` | Keepalive ping | - |

#### Server → Client

| Type | Purpose | Data Fields |
|------|---------|------------|
| `connected` | Connection confirmed | `participant_type`, `participant_id` |
| `message` | New message received | Full message object |
| `typing` | Someone is typing | `chat_id`, `participant_type`, `participant_id`, `is_typing` |
| `read_receipt` | Message was read | `chat_id`, `message_id`, `reader_type`, `reader_id` |
| `user_joined` | Someone joined chat | `chat_id`, `participant_type`, `participant_id` |
| `user_left` | Someone left chat | `chat_id`, `participant_type`, `participant_id` |
| `error` | Error occurred | `error` |
| `pong` | Response to ping | `timestamp` |

### Message Examples

#### Join Chat

```javascript
ws.send(JSON.stringify({
  type: 'join_chat',
  chat_id: 1
}));
```

#### Send Text Message

```javascript
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: 1,
  content: 'Hello, how can I help you?',
  message_type: 'text'
}));
```

#### Send Image Message

First, upload the image via REST API, then:

```javascript
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: 1,
  content: 'Check out this photo',
  message_type: 'image',
  media_url: '/uploads/chat/image.jpg'
}));
```

#### Reply to Message

```javascript
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: 1,
  content: 'That sounds great!',
  message_type: 'text',
  reply_to_message_id: 101
}));
```

#### Send Typing Indicator

```javascript
// Start typing
ws.send(JSON.stringify({
  type: 'typing',
  chat_id: 1,
  is_typing: true
}));

// Stop typing
ws.send(JSON.stringify({
  type: 'typing',
  chat_id: 1,
  is_typing: false
}));
```

#### Mark Message as Read

```javascript
ws.send(JSON.stringify({
  type: 'read_message',
  chat_id: 1,
  message_id: 101
}));
```

---

## Implementation Examples

### Vanilla JavaScript

```javascript
class ChatClient {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.listeners = {};
  }

  connect() {
    const wsUrl = `ws://localhost:8000/api/v1/chat/ws/chat/user?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Connected');
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.emit(data.type, data);
    };

    this.ws.onerror = (error) => {
      console.error('Error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('Disconnected');
      this.emit('disconnected');
      // Auto-reconnect after 3 seconds
      setTimeout(() => this.connect(), 3000);
    };
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  joinChat(chatId) {
    this.send({ type: 'join_chat', chat_id: chatId });
  }

  leaveChat(chatId) {
    this.send({ type: 'leave_chat', chat_id: chatId });
  }

  sendMessage(chatId, content, messageType = 'text') {
    this.send({
      type: 'send_message',
      chat_id: chatId,
      content: content,
      message_type: messageType
    });
  }

  sendTyping(chatId, isTyping) {
    this.send({
      type: 'typing',
      chat_id: chatId,
      is_typing: isTyping
    });
  }

  markAsRead(chatId, messageId) {
    this.send({
      type: 'read_message',
      chat_id: chatId,
      message_id: messageId
    });
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const chat = new ChatClient(localStorage.getItem('token'));
chat.connect();

chat.on('connected', () => {
  console.log('Chat connected');
  chat.joinChat(1);
});

chat.on('message', (data) => {
  console.log('New message:', data.message);
  // Update UI with new message
});

chat.on('typing', (data) => {
  console.log(`${data.participant_id} is ${data.is_typing ? 'typing' : 'stopped typing'}`);
  // Show/hide typing indicator
});
```

---

## Complete React Integration

### Hook: `useChatWebSocket`

```jsx
import { useEffect, useRef, useState, useCallback } from 'react';

export const useChatWebSocket = (token, onMessage) => {
  const ws = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentChatId, setCurrentChatId] = useState(null);

  useEffect(() => {
    if (!token) return;

    const wsUrl = `ws://localhost:8000/api/v1/chat/ws/chat/user?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          console.log('Connection confirmed');
          break;
        case 'message':
          onMessage(data.message);
          break;
        case 'typing':
          // Handle typing indicator
          break;
        case 'read_receipt':
          // Handle read receipt
          break;
        default:
          console.log('Unknown message type:', data.type);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      
      // Auto-reconnect after 3 seconds
      setTimeout(() => {
        if (ws.current) {
          ws.current = null;
        }
      }, 3000);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token, onMessage]);

  const send = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  const joinChat = useCallback((chatId) => {
    send({ type: 'join_chat', chat_id: chatId });
    setCurrentChatId(chatId);
  }, [send]);

  const leaveChat = useCallback((chatId) => {
    send({ type: 'leave_chat', chat_id: chatId });
    if (currentChatId === chatId) {
      setCurrentChatId(null);
    }
  }, [send, currentChatId]);

  const sendMessage = useCallback((chatId, content, messageType = 'text') => {
    send({
      type: 'send_message',
      chat_id: chatId,
      content: content,
      message_type: messageType
    });
  }, [send]);

  const sendTyping = useCallback((chatId, isTyping) => {
    send({
      type: 'typing',
      chat_id: chatId,
      is_typing: isTyping
    });
  }, [send]);

  const markAsRead = useCallback((chatId, messageId) => {
    send({
      type: 'read_message',
      chat_id: chatId,
      message_id: messageId
    });
  }, [send]);

  return {
    isConnected,
    joinChat,
    leaveChat,
    sendMessage,
    sendTyping,
    markAsRead,
    currentChatId
  };
};
```

### Component: `ChatWindow`

```jsx
import React, { useState, useEffect, useRef } from 'react';
import { useChatWebSocket } from './useChatWebSocket';

const ChatWindow = ({ chatId, token }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const handleNewMessage = (message) => {
    setMessages(prev => [...prev, message]);
    
    // Mark as read if chat is visible
    if (document.hasFocus()) {
      markAsRead(chatId, message.id);
    }
  };

  const {
    isConnected,
    joinChat,
    leaveChat,
    sendMessage,
    sendTyping,
    markAsRead
  } = useChatWebSocket(token, handleNewMessage);

  useEffect(() => {
    if (isConnected && chatId) {
      joinChat(chatId);
      // Fetch message history via REST API
      fetchMessageHistory(chatId);
    }

    return () => {
      if (chatId) {
        leaveChat(chatId);
      }
    };
  }, [isConnected, chatId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchMessageHistory = async (chatId) => {
    const response = await fetch(
      `http://localhost:8000/api/v1/chat/chats/${chatId}/messages`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    const data = await response.json();
    setMessages(data.messages.reverse());
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);

    // Send typing indicator
    if (!isTyping) {
      setIsTyping(true);
      sendTyping(chatId, true);
    }

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Stop typing after 2 seconds of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      sendTyping(chatId, false);
    }, 2000);
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    sendMessage(chatId, inputValue);
    setInputValue('');

    // Stop typing indicator
    if (isTyping) {
      setIsTyping(false);
      sendTyping(chatId, false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h3>Chat #{chatId}</h3>
        <span className={isConnected ? 'status-connected' : 'status-disconnected'}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div className="messages-container">
        {messages.map(message => (
          <div key={message.id} className={`message ${message.sender_type}`}>
            <div className="message-sender">{message.sender_name}</div>
            <div className="message-content">{message.content}</div>
            <div className="message-time">
              {new Date(message.created_at).toLocaleTimeString()}
            </div>
            {message.read_receipts && message.read_receipts.length > 0 && (
              <div className="read-receipts">✓✓</div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="message-input">
        <textarea
          value={inputValue}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder="Type a message..."
          rows="2"
        />
        <button onClick={handleSendMessage} disabled={!isConnected}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatWindow;
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 1008 Policy Violation | Invalid token or authentication failed | Check token validity, re-authenticate |
| Connection refused | Server not running or wrong URL | Verify server status and URL |
| Message not sent | Not joined to chat | Call `join_chat` before sending messages |
| Disconnected frequently | Network issues or server overload | Implement auto-reconnect logic |

### Error Handling Example

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  
  // Show user-friendly error
  showNotification('Connection error. Retrying...', 'error');
  
  // Try to reconnect
  setTimeout(() => reconnect(), 3000);
};

ws.onclose = (event) => {
  if (event.code === 1008) {
    // Authentication failed
    console.error('Authentication failed');
    redirectToLogin();
  } else {
    // Other disconnect reasons
    console.log('Disconnected:', event.reason);
    attemptReconnect();
  }
};
```

---

## Best Practices

### 1. Connection Management

- ✅ **Auto-reconnect** on disconnect
- ✅ **Heartbeat/ping** every 30-60 seconds to keep connection alive
- ✅ **Graceful degradation**: Fall back to HTTP polling if WebSocket fails
- ✅ **Token refresh**: Handle expired tokens and re-authenticate

### 2. Message Handling

- ✅ **Optimistic UI**: Show message immediately, update on confirmation
- ✅ **Queue messages**: If offline, queue messages and send when reconnected
- ✅ **Deduplicate**: Use message IDs to prevent duplicates
- ✅ **Persist locally**: Store messages in IndexedDB/LocalStorage

### 3. Performance

- ✅ **Lazy load**: Fetch old messages on demand (pagination)
- ✅ **Virtual scrolling**: For long message lists
- ✅ **Debounce typing**: Don't send typing indicator on every keystroke
- ✅ **Batch read receipts**: Mark multiple messages as read in one call

### 4. User Experience

- ✅ **Show connection status**: Visual indicator for connected/disconnected
- ✅ **Typing indicators**: Show when other party is typing
- ✅ **Read receipts**: Show when messages are read
- ✅ **Online presence**: Show who's currently online
- ✅ **Notifications**: Browser/push notifications for new messages

### 5. Security

- ✅ **HTTPS/WSS in production**: Use secure WebSocket (wss://)
- ✅ **Validate messages**: Sanitize user input
- ✅ **Rate limiting**: Implement client-side rate limiting
- ✅ **Token expiry**: Handle token refresh gracefully

---

## Production Deployment

### Environment Variables

```bash
# Frontend
REACT_APP_WS_URL=wss://api.yourdomain.com/api/v1/chat/ws/chat/user
REACT_APP_API_URL=https://api.yourdomain.com/api/v1

# Backend
# Update CORS settings to allow your frontend domain
```

### Nginx Configuration

```nginx
# WebSocket proxy
location /api/v1/chat/ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    # Increase timeouts for WebSocket
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

---

## Testing

### Manual Testing Tools

**1. Postman / Insomnia**
- Create WebSocket request
- Use token in URL
- Send JSON messages

**2. Browser DevTools**
```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_TOKEN');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({ type: 'join_chat', chat_id: 1 }));
```

**3. wscat CLI tool**
```bash
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_TOKEN"
```

---

## Support & Troubleshooting

### Debug Mode

Enable verbose logging:

```javascript
const DEBUG = true;

if (DEBUG) {
  ws.onmessage = (event) => {
    console.log('[WS Received]:', event.data);
    // Your message handling
  };
  
  // Override send to log
  const originalSend = ws.send;
  ws.send = function(data) {
    console.log('[WS Sent]:', data);
    originalSend.call(ws, data);
  };
}
```

### Common Issues

**Q: Messages not received in real-time**
- Check if you've joined the chat (`join_chat`)
- Verify WebSocket connection is open
- Check browser console for errors

**Q: Typing indicator not working**
- Ensure you're sending `typing` events
- Check if other participant has joined the chat
- Verify WebSocket connection for recipient

**Q: Read receipts not showing**
- Confirm you're sending `read_message` events
- Check if message sender is online to receive receipt
- Verify message ID is correct

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **WebSocket Testing Tool**: static/sse_test.html (adapted for WebSocket)
- **Backend Code**: `app/api/v1/endpoints/chat_websocket.py`
- **Models**: `app/models/chat_models.py`

---

**Questions?** Check server logs or contact the backend team for support.

