# Chat System - Quick Reference

## 🚀 Quick Start (30 seconds)

### Backend Setup
```bash
# 1. Run migration
alembic upgrade head

# 2. Start server
uvicorn app.main:app --reload
```

### Frontend Connection
```javascript
// 1. Connect
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_JWT_TOKEN');

// 2. Join chat
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join_chat', chat_id: 1 }));
};

// 3. Send message
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: 1,
  content: 'Hello!'
}));

// 4. Receive messages
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log('Received:', data);
};
```

---

## 📡 WebSocket Endpoints

| User Type | WebSocket URL |
|-----------|---------------|
| **Admin/Staff** | `ws://localhost:8000/api/v1/chat/ws/chat/user?token={JWT}` |
| **Customer** | `ws://localhost:8000/api/v1/chat/ws/chat/customer?token={JWT}` |

---

## 🔌 REST API Endpoints

### Chat Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/chat/chats` | Create chat (admin) |
| `POST` | `/api/v1/chat/chats/customer` | Create chat (customer) |
| `GET` | `/api/v1/chat/chats` | List chats (admin) |
| `GET` | `/api/v1/chat/chats/customer` | List chats (customer) |
| `GET` | `/api/v1/chat/chats/{id}` | Get chat details |
| `GET` | `/api/v1/chat/chats/{id}/messages` | Get message history |
| `POST` | `/api/v1/chat/chats/{id}/messages` | Send message (HTTP) |
| `PUT` | `/api/v1/chat/messages/{id}` | Edit message |
| `DELETE` | `/api/v1/chat/messages/{id}` | Delete message |
| `POST` | `/api/v1/chat/upload` | Upload file |
| `GET` | `/api/v1/chat/stats` | Get chat statistics |

---

## 📨 WebSocket Message Types

### Client → Server
```javascript
// Join chat
{ type: 'join_chat', chat_id: 1 }

// Leave chat
{ type: 'leave_chat', chat_id: 1 }

// Send text message
{ type: 'send_message', chat_id: 1, content: 'Hello', message_type: 'text' }

// Send image
{ type: 'send_message', chat_id: 1, media_url: '/uploads/image.jpg', message_type: 'image' }

// Typing indicator
{ type: 'typing', chat_id: 1, is_typing: true }

// Mark as read
{ type: 'read_message', chat_id: 1, message_id: 101 }

// Keepalive
{ type: 'ping' }
```

### Server → Client
```javascript
// Connection confirmed
{ type: 'connected', participant_type: 'user', participant_id: 456 }

// New message
{ type: 'message', message: { id: 101, content: 'Hello', ... } }

// Typing indicator
{ type: 'typing', chat_id: 1, participant_id: 123, is_typing: true }

// Read receipt
{ type: 'read_receipt', chat_id: 1, message_id: 101, reader_id: 123 }

// User joined
{ type: 'user_joined', chat_id: 1, participant_id: 789 }

// User left
{ type: 'user_left', chat_id: 1, participant_id: 789 }

// Error
{ type: 'error', error: 'Error message' }

// Pong
{ type: 'pong', timestamp: '2026-01-09T10:30:00' }
```

---

## 🎨 Features Supported

### ✅ Core Features
- [x] Real-time messaging via WebSocket
- [x] Multiple concurrent conversations
- [x] Text messages
- [x] Image messages
- [x] Voice notes
- [x] Message editing (15 min window)
- [x] Message deletion (soft delete)
- [x] Reply to messages

### ✅ Advanced Features
- [x] Read receipts
- [x] Typing indicators
- [x] Online presence
- [x] Unread message count
- [x] Message history pagination
- [x] File upload
- [x] Entity references (appointments, products, packs)
- [x] Multiple participants per chat
- [x] Chat archiving

### ✅ Technical Features
- [x] Auto-reconnect support
- [x] JWT authentication
- [x] Salon-specific isolation
- [x] Connection statistics
- [x] Detachable architecture

---

## 📂 File Structure

```
app/
├── models/
│   └── chat_models.py          # Database models
├── schemas/
│   └── chat_schemas.py         # Pydantic schemas
├── api/v1/endpoints/
│   ├── chat.py                 # REST API endpoints
│   └── chat_websocket.py       # WebSocket endpoints
├── core/
│   └── chat_manager.py         # WebSocket connection manager
└── alembic/versions/
    └── 027_add_chat_tables.py  # Database migration

docs/
├── CHAT_FRONTEND_INTEGRATION.md   # Full integration guide
└── CHAT_QUICKREF.md               # This file
```

---

## 🔍 Example Flow

### 1. Admin initiates chat with customer

```javascript
// Step 1: Create chat via REST API
const response = await fetch('/api/v1/chat/chats', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    customer_id: 123,
    initial_message: 'Hi, how can I help?'
  })
});
const chat = await response.json();

// Step 2: Connect WebSocket
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/chat/user?token=${token}`);

// Step 3: Join chat
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join_chat', chat_id: chat.id }));
};

// Step 4: Send messages
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: chat.id,
  content: 'What can I help you with?'
}));

// Step 5: Receive messages
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'message') {
    displayMessage(data.message);
  }
};
```

### 2. Customer receives and responds

```javascript
// Step 1: Connect WebSocket
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/chat/customer?token=${customerToken}`);

// Step 2: Join chat (customer gets chat ID from list or notification)
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join_chat', chat_id: 1 }));
};

// Step 3: Receive admin's message
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'message') {
    displayMessage(data.message);
    
    // Mark as read
    ws.send(JSON.stringify({
      type: 'read_message',
      chat_id: data.message.chat_id,
      message_id: data.message.id
    }));
  }
};

// Step 4: Reply
ws.send(JSON.stringify({
  type: 'send_message',
  chat_id: 1,
  content: 'I need to book an appointment'
}));
```

---

## 🐛 Debugging

### Check Connection Status
```javascript
console.log('WebSocket state:', ws.readyState);
// 0: CONNECTING
// 1: OPEN
// 2: CLOSING
// 3: CLOSED
```

### Enable Debug Logging
```javascript
ws.onmessage = (e) => {
  console.log('[Received]', e.data);
  // Your handling code
};

const originalSend = ws.send.bind(ws);
ws.send = (data) => {
  console.log('[Sent]', data);
  originalSend(data);
};
```

### Test with curl
```bash
# Test REST API
curl -X POST http://localhost:8000/api/v1/chat/chats \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "initial_message": "Test"}'

# Test WebSocket with wscat
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/chat/ws/chat/user?token=YOUR_TOKEN"
```

---

## 🔐 Authentication

### Get Token (Admin)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@salon.com&password=password"
```

### Get Token (Customer)
```bash
curl -X POST http://localhost:8000/api/v1/customer-auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "password": "password"}'
```

---

## 📊 Database Models

### Key Tables
- **chats**: Main chat conversations
- **chat_participants**: Links users/customers to chats
- **chat_messages**: Individual messages
- **chat_message_reads**: Read receipt tracking
- **chat_attachments**: Additional file attachments

### Entity Relationships
```
Chat (1) ─── (Many) ChatParticipant ─── (1) User/Customer
Chat (1) ─── (Many) ChatMessage ─── (Many) ChatMessageRead
ChatMessage (1) ─── (Many) ChatAttachment
```

---

## ⚡ Performance Tips

1. **Pagination**: Use `page` and `page_size` for message history
2. **Lazy Load**: Fetch old messages only when needed
3. **Debounce Typing**: Don't send typing on every keystroke
4. **Batch Reads**: Mark multiple messages as read together
5. **Virtual Scrolling**: For long message lists
6. **IndexedDB**: Cache messages locally

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Can't connect | Check token validity and server status |
| Messages not received | Ensure you've called `join_chat` |
| Typing not showing | Both parties must be in same chat |
| Read receipts missing | Sender must be online to receive |
| Connection drops | Implement auto-reconnect with exponential backoff |

---

## 📚 Full Documentation

- **Complete Guide**: [CHAT_FRONTEND_INTEGRATION.md](./CHAT_FRONTEND_INTEGRATION.md)
- **API Docs**: http://localhost:8000/docs
- **Models**: `app/models/chat_models.py`
- **WebSocket**: `app/api/v1/endpoints/chat_websocket.py`
- **REST API**: `app/api/v1/endpoints/chat.py`

---

## 💡 Next Steps

1. Run migration: `alembic upgrade head`
2. Test WebSocket connection
3. Integrate into your frontend
4. Add file upload functionality
5. Implement push notifications
6. Add message search
7. Deploy to production with WSS

---

**Need Help?** Check the full integration guide or server logs for detailed information.
