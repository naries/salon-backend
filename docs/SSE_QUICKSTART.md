# SSE Notifications - Quick Start Guide

This guide will help you get started with real-time Server-Sent Events (SSE) notifications in 5 minutes.

## Prerequisites

- Salon backend server running
- Valid JWT tokens for testing (admin or customer)
- Modern web browser or API client

## Step 1: Start the Server

```bash
cd /Users/ajiboyeayobami/Documents/salon-backend
uvicorn app.main:app --reload
```

Server will be available at `http://localhost:8000`

## Step 2: Get a JWT Token

### For Admin Users

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=your_password"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### For Customers

```bash
curl -X POST http://localhost:8000/api/v1/customer-auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "password": "customer_password"}'
```

## Step 3: Connect to SSE Stream

### Option A: Browser HTML Client (Easiest)

1. Open the test client in your browser:
   ```bash
   open static/sse_test.html
   ```

2. Enter your JWT token
3. Select user type (Admin or Customer)
4. Click "Connect"
5. Watch notifications arrive in real-time!

### Option B: cURL (Terminal)

```bash
# Admin notifications
curl -N "http://localhost:8000/api/v1/notifications/stream?token=YOUR_JWT_TOKEN"

# Customer notifications
curl -N "http://localhost:8000/api/v1/notifications/customer/stream?token=YOUR_JWT_TOKEN"

# Customer notifications filtered by salon
curl -N "http://localhost:8000/api/v1/notifications/customer/stream?token=YOUR_JWT_TOKEN&salon_id=1"
```

### Option C: JavaScript in Browser Console

```javascript
const token = "YOUR_JWT_TOKEN";
const eventSource = new EventSource(`/api/v1/notifications/stream?token=${token}`);

eventSource.addEventListener('connected', (e) => {
    console.log('Connected:', JSON.parse(e.data));
});

eventSource.addEventListener('notification', (e) => {
    const notif = JSON.parse(e.data);
    console.log('📬 New notification:', notif.title, '-', notif.message);
});

eventSource.addEventListener('ping', (e) => {
    console.log('💓 Keepalive');
});
```

## Step 4: Send Test Notifications

### Option A: Python Test Script

```bash
# In a new terminal
python test_sse_notifications.py
```

Follow the interactive menu to:
1. View connection statistics
2. Send notifications to salons
3. Send notifications to specific users
4. Run stress tests

### Option B: Create Notification via API

When you create appointments, bookings, or any action that triggers notifications, they'll automatically be pushed to connected SSE clients.

Example - trigger a notification through appointment creation:

```bash
curl -X POST http://localhost:8000/api/v1/appointments \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "service_id": 1,
    "sub_service_id": 1,
    "appointment_date": "2024-01-20",
    "start_time": "10:00:00"
  }'
```

## Step 5: Monitor Active Connections

```bash
# Get connection statistics (superadmin only)
curl http://localhost:8000/api/v1/notifications/stream/stats \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

Response:
```json
{
  "active_admin_connections": 2,
  "active_customer_connections": 5,
  "total_connections": 7,
  "admins": [[1, 101], [1, 102]],
  "customers": [501, 502, 503, 504, 505]
}
```

## Understanding the Flow

```
┌─────────────────┐
│  Salon Admin    │
│   Browser       │
└────────┬────────┘
         │ Connect to /stream?token=xxx
         ▼
┌─────────────────────────────┐
│   SSE Notification Stream   │
│   (salon_id filtered)       │
└────────┬────────────────────┘
         │ Receives events:
         │ • connected
         │ • notification
         │ • ping
         ▼
┌─────────────────────────────┐
│  Browser displays           │
│  notification in real-time  │
└─────────────────────────────┘


Meanwhile...

┌─────────────────┐
│ Backend Service │
└────────┬────────┘
         │ Creates notification
         ▼
┌─────────────────────────────┐
│  NotificationService        │
│  _save_notification()       │
└────────┬────────────────────┘
         │ Saves to DB
         │ Pushes to SSE queue
         ▼
┌─────────────────────────────┐
│  NotificationManager        │
│  Routes by salon_id         │
└────────┬────────────────────┘
         │ Pushes to connected
         │ admin's queue
         ▼
┌─────────────────────────────┐
│  Admin receives instantly!  │
└─────────────────────────────┘
```

## Notification Types by Recipient

### 1. Salon-Wide Notifications (`recipient_type: "salon"`)
Sent to ALL admins in the salon:
- New appointment bookings
- Customer complaints
- System alerts

### 2. Specific Admin Notifications (`recipient_type: "user"`)
Sent to ONE specific admin:
- Personal reminders
- Direct messages
- Role-specific alerts

### 3. Customer Notifications (`recipient_type: "customer"`)
Sent to customers:
- Appointment confirmations
- Appointment reminders
- Order updates

## Testing Checklist

- [ ] Admin can connect to SSE stream
- [ ] Customer can connect to SSE stream
- [ ] Connection confirmation received
- [ ] Keepalive pings received every 30s
- [ ] Notifications pushed in real-time
- [ ] Salon filtering works correctly
- [ ] Multiple connections work simultaneously
- [ ] Reconnection works after disconnect
- [ ] Token authentication validates properly
- [ ] Stats endpoint shows accurate counts

## Common Issues & Solutions

### Issue: "Authentication required"
**Solution**: Make sure JWT token is valid and not expired

### Issue: "User is not associated with a salon"
**Solution**: Admin user must have a salon_id set in the database

### Issue: Not receiving notifications
**Solution**: 
1. Check connection is established (should see "connected" event)
2. Verify notification has matching salon_id
3. Check browser console for errors
4. Ensure server is running

### Issue: Connection keeps dropping
**Solution**:
1. Check network stability
2. Verify server is not behind aggressive proxy timeout
3. Monitor keepalive pings (should be every 30s)

## Next Steps

1. **Integrate with Frontend**: Use the JavaScript examples in your React/Vue/Angular app
2. **Add Browser Notifications**: Request permission and show native notifications
3. **Implement Notification UI**: Create notification bell/panel in your app
4. **Add Mark as Read**: Use existing notification endpoints to mark notifications read
5. **Production Deploy**: Configure Nginx for SSE (see docs/SSE_NOTIFICATIONS.md)

## Learn More

- Full documentation: `docs/SSE_NOTIFICATIONS.md`
- API reference: http://localhost:8000/docs
- Test client: `static/sse_test.html`
- Test script: `test_sse_notifications.py`

## Support

If you encounter issues:
1. Check server logs for errors
2. Review SSE_NOTIFICATIONS.md for detailed troubleshooting
3. Test with the HTML client first to isolate issues
4. Verify token and user permissions

---

**Ready to go!** 🚀 Start the server and open `static/sse_test.html` to see notifications in action.
