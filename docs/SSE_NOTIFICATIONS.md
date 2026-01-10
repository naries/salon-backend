# Server-Sent Events (SSE) Notifications

## Overview

The salon backend implements Server-Sent Events (SSE) for real-time push notifications to salon admins and customers. SSE provides a simple, one-way communication channel from server to client, perfect for notification delivery.

## Why SSE Over WebSockets?

- **Simpler Protocol**: SSE uses standard HTTP, no special protocol upgrade needed
- **Auto-Reconnect**: Browsers automatically reconnect on connection loss
- **One-Way Communication**: Perfect for notifications (server → client only)
- **Better for Notifications**: No need for bidirectional communication
- **HTTP/2 Compatible**: Works efficiently with HTTP/2 multiplexing

## Architecture

### Components

1. **NotificationManager** (`app/core/notification_manager.py`)
   - Manages SSE connections per salon and per user
   - Maintains separate queues for admins and customers
   - Handles connection lifecycle and cleanup

2. **SSE Endpoints** (`app/api/v1/endpoints/notifications.py`)
   - `/api/v1/notifications/stream` - Salon admin notifications
   - `/api/v1/notifications/customer/stream` - Customer notifications
   - `/api/v1/notifications/stream/stats` - Connection statistics (superadmin only)

3. **Notification Service** (`app/services/notification_service.py`)
   - Pushes notifications to SSE queues when created
   - Handles salon-specific routing

## API Endpoints

### Admin Notification Stream

```http
GET /api/v1/notifications/stream
Authorization: Bearer {admin_token}
```

**Response**: SSE stream with events:
- `connected` - Connection established
- `notification` - New notification data
- `ping` - Keepalive message (every 30 seconds)

**Features**:
- Automatically filters by admin's salon_id
- Only admins associated with a salon can connect
- Each admin gets their own queue

### Customer Notification Stream

```http
GET /api/v1/notifications/customer/stream?salon_id={optional_salon_id}
Authorization: Bearer {customer_token}
```

**Query Parameters**:
- `salon_id` (optional) - Filter notifications for specific salon

**Response**: Same SSE event structure as admin stream

### Connection Statistics

```http
GET /api/v1/notifications/stream/stats
Authorization: Bearer {superadmin_token}
```

**Response**:
```json
{
  "active_admin_connections": 5,
  "active_customer_connections": 12,
  "total_connections": 17,
  "admins": [[1, 101], [1, 102], [2, 103]],
  "customers": [501, 502, 503]
}
```

## Client Implementation

### JavaScript/Browser

```javascript
// Connect to notification stream
const eventSource = new EventSource('/api/v1/notifications/stream', {
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
});

// Handle connection established
eventSource.addEventListener('connected', (event) => {
  const data = JSON.parse(event.data);
  console.log('Connected to notifications:', data);
});

// Handle new notifications
eventSource.addEventListener('notification', (event) => {
  const notification = JSON.parse(event.data);
  console.log('New notification:', notification);
  
  // Display notification to user
  showNotification(notification);
});

// Handle keepalive pings
eventSource.addEventListener('ping', (event) => {
  const data = JSON.parse(event.data);
  console.log('Keepalive ping:', data.timestamp);
});

// Handle errors and reconnection
eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Browser will automatically attempt to reconnect
};

// Close connection when done
// eventSource.close();
```

### React Example

```jsx
import { useEffect, useState } from 'react';

function NotificationStream({ token }) {
  const [notifications, setNotifications] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(
      '/api/v1/notifications/stream',
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    eventSource.addEventListener('connected', (event) => {
      setConnected(true);
      console.log('Connected:', JSON.parse(event.data));
    });

    eventSource.addEventListener('notification', (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev]);
      
      // Show browser notification
      if (Notification.permission === 'granted') {
        new Notification(notification.title, {
          body: notification.message,
          icon: '/notification-icon.png'
        });
      }
    });

    eventSource.onerror = (error) => {
      setConnected(false);
      console.error('Connection error:', error);
    };

    return () => {
      eventSource.close();
    };
  }, [token]);

  return (
    <div>
      <div>Status: {connected ? 'Connected' : 'Disconnected'}</div>
      <ul>
        {notifications.map(notif => (
          <li key={notif.id}>
            <strong>{notif.title}</strong>: {notif.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Python Client Example

```python
import sseclient
import requests

def listen_to_notifications(token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        'http://localhost:8000/api/v1/notifications/stream',
        headers=headers,
        stream=True
    )
    
    client = sseclient.SSEClient(response)
    
    for event in client.events():
        if event.event == 'notification':
            notification = json.loads(event.data)
            print(f"New notification: {notification['title']}")
        elif event.event == 'connected':
            print("Connected to notification stream")
        elif event.event == 'ping':
            print("Keepalive ping received")
```

## Notification Data Structure

Each notification event contains:

```json
{
  "id": 123,
  "notification_type": "appointment_confirmed",
  "title": "Appointment Confirmed",
  "message": "Your appointment has been confirmed for tomorrow at 2 PM",
  "recipient_type": "customer",
  "recipient_id": 456,
  "salon_id": 1,
  "entity_type": "appointment",
  "entity_id": 789,
  "is_read": false,
  "created_at": "2024-01-15T10:30:00",
  "extra_data": {
    "appointment_date": "2024-01-16T14:00:00",
    "service_name": "Haircut"
  }
}
```

## Notification Routing

### Salon-Specific Routing

The system automatically routes notifications based on `recipient_type` and `salon_id`:

1. **`recipient_type: "salon"`**
   - Sent to ALL admins in the salon
   - Uses `salon_id` to identify target salon
   - All connected admins receive the notification

2. **`recipient_type: "user"`**
   - Sent to a SPECIFIC admin user
   - Uses `salon_id` and `recipient_id`
   - Only the specific admin receives it

3. **`recipient_type: "customer"`**
   - Sent to a specific customer
   - Uses `recipient_id`
   - Can be filtered by `salon_id` on client side

### Example Flow

```python
# When an appointment is booked
notification_service.send_notification(
    notification_type="new_appointment",
    title="New Appointment",
    message="You have a new appointment booking",
    recipient_type="salon",  # Send to all admins
    recipient_id=None,
    salon_id=salon.id,  # Which salon
    entity_type="appointment",
    entity_id=appointment.id
)
```

## Connection Management

### Keepalive

- Server sends `ping` events every 30 seconds
- Prevents connection timeout
- Client should monitor for pings to detect connection issues

### Auto-Reconnect

- Browsers automatically reconnect on connection loss
- Exponential backoff on repeated failures
- Client receives `connected` event on successful reconnection

### Cleanup

- Connections automatically cleaned up on disconnect
- Queues are removed when clients disconnect
- Memory efficient - no lingering connections

## Testing

### Manual Testing with cURL

```bash
# Test admin stream (replace with valid token)
curl -N -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  http://localhost:8000/api/v1/notifications/stream

# Test customer stream
curl -N -H "Authorization: Bearer YOUR_CUSTOMER_TOKEN" \
  http://localhost:8000/api/v1/notifications/customer/stream

# Test with salon filter
curl -N -H "Authorization: Bearer YOUR_CUSTOMER_TOKEN" \
  "http://localhost:8000/api/v1/notifications/customer/stream?salon_id=1"
```

### Testing with httpie

```bash
# Admin stream
http --stream GET localhost:8000/api/v1/notifications/stream \
  Authorization:"Bearer YOUR_TOKEN"

# Check connection stats (superadmin only)
http GET localhost:8000/api/v1/notifications/stream/stats \
  Authorization:"Bearer YOUR_SUPERADMIN_TOKEN"
```

## Production Considerations

### Nginx Configuration

When deploying behind Nginx, ensure SSE support:

```nginx
location /api/v1/notifications/stream {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    
    # Disable buffering for SSE
    proxy_buffering off;
    proxy_cache off;
    
    # Keep connection alive
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

### Load Balancing

- Use sticky sessions (session affinity) with load balancers
- SSE connections are stateful and tied to specific backend instances
- Consider using Redis pub/sub for multi-instance deployments

### Scalability

Current implementation is single-instance. For multi-instance:

1. **Redis Pub/Sub**: Share notification events across instances
2. **Sticky Sessions**: Route same client to same instance
3. **Message Queue**: Use RabbitMQ or similar for event distribution

### Monitoring

Monitor these metrics:

- Active connection count (`/api/v1/notifications/stream/stats`)
- Connection duration
- Notification delivery latency
- Failed deliveries

## Error Handling

### Client-Side

```javascript
eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  
  if (eventSource.readyState === EventSource.CLOSED) {
    // Connection closed, attempt manual reconnect after delay
    setTimeout(() => {
      // Reconnect logic
    }, 5000);
  }
  // Otherwise, browser handles reconnection automatically
};
```

### Server-Side

- Graceful cleanup on client disconnect
- Exception handling in event generators
- Logging for debugging connection issues

## Security

### Authentication

- JWT token required in Authorization header
- Token validates user/customer identity
- Salon association verified before connection

### Authorization

- Admins only receive notifications for their salon
- Customers only receive their own notifications
- Superadmin required for stats endpoint

### Rate Limiting

Consider implementing:
- Connection rate limits per user
- Maximum connections per salon
- Request throttling on stats endpoint

## Troubleshooting

### Connection Not Established

1. Check JWT token validity
2. Verify user has salon_id (for admins)
3. Check server logs for errors
4. Ensure browser supports SSE

### No Notifications Received

1. Verify notifications are being created in database
2. Check notification `salon_id` matches user's salon
3. Monitor server logs for push attempts
4. Test with `/stream/stats` to see active connections

### Connection Drops

1. Check network stability
2. Verify keepalive pings are received
3. Check Nginx/proxy timeout settings
4. Monitor server resource usage

## Future Enhancements

- [ ] Redis pub/sub for multi-instance support
- [ ] Notification priority levels
- [ ] Custom notification filtering on client
- [ ] Notification batching for performance
- [ ] WebSocket fallback option
- [ ] Push notification integration with SSE
- [ ] Delivery acknowledgment tracking
