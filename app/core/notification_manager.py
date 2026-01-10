"""
SSE Notification Manager
Manages Server-Sent Events connections for real-time notifications
"""
import asyncio
import json
from typing import Dict, AsyncGenerator, Optional
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages SSE connections for real-time notifications.
    Maintains separate queues per salon and per user.
    """
    
    def __init__(self):
        # Queues for salon admins: {(salon_id, user_id): Queue}
        self.admin_queues: Dict[tuple, asyncio.Queue] = {}
        
        # Queues for customers: {customer_id: Queue}
        self.customer_queues: Dict[int, asyncio.Queue] = {}
        
        # Track active connections
        self.active_connections = {
            'admins': set(),
            'customers': set()
        }
    
    def get_admin_queue(self, salon_id: int, user_id: int) -> asyncio.Queue:
        """Get or create queue for salon admin"""
        key = (salon_id, user_id)
        if key not in self.admin_queues:
            self.admin_queues[key] = asyncio.Queue()
            self.active_connections['admins'].add(key)
        return self.admin_queues[key]
    
    def get_customer_queue(self, customer_id: int) -> asyncio.Queue:
        """Get or create queue for customer"""
        if customer_id not in self.customer_queues:
            self.customer_queues[customer_id] = asyncio.Queue()
            self.active_connections['customers'].add(customer_id)
        return self.customer_queues[customer_id]
    
    async def send_to_salon_admins(self, salon_id: int, notification: dict):
        """Send notification to all connected admins of a salon"""
        sent_count = 0
        
        # Find all admin queues for this salon
        for (s_id, u_id), queue in list(self.admin_queues.items()):
            if s_id == salon_id:
                try:
                    await queue.put(notification)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending to admin {u_id} in salon {salon_id}: {e}")
        
        logger.info(f"Sent notification to {sent_count} admin(s) in salon {salon_id}")
        return sent_count
    
    async def send_to_specific_admin(self, salon_id: int, user_id: int, notification: dict):
        """Send notification to a specific admin"""
        key = (salon_id, user_id)
        if key in self.admin_queues:
            try:
                await self.admin_queues[key].put(notification)
                logger.info(f"Sent notification to admin {user_id} in salon {salon_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending to admin {user_id}: {e}")
                return False
        return False
    
    async def send_to_customer(self, customer_id: int, notification: dict):
        """Send notification to a specific customer"""
        if customer_id in self.customer_queues:
            try:
                await self.customer_queues[customer_id].put(notification)
                logger.info(f"Sent notification to customer {customer_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending to customer {customer_id}: {e}")
                return False
        return False
    
    async def admin_event_stream(self, salon_id: int, user_id: int) -> AsyncGenerator:
        """
        Generate SSE stream for salon admin.
        Yields notifications for the specific salon.
        """
        queue = self.get_admin_queue(salon_id, user_id)
        
        try:
            # Send connection confirmation
            yield {
                "event": "connected",
                "data": json.dumps({
                    "message": "Connected to notification stream",
                    "salon_id": salon_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            # Keep connection alive and send notifications
            while True:
                try:
                    # Wait for notification with timeout for keepalive
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    yield {
                        "event": "notification",
                        "data": json.dumps(notification)
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {
                        "event": "ping",
                        "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                    }
                    
        except asyncio.CancelledError:
            logger.info(f"Admin {user_id} from salon {salon_id} disconnected")
        finally:
            # Cleanup on disconnect
            key = (salon_id, user_id)
            if key in self.admin_queues:
                del self.admin_queues[key]
            if key in self.active_connections['admins']:
                self.active_connections['admins'].remove(key)
    
    async def customer_event_stream(self, customer_id: int, salon_id: Optional[int] = None) -> AsyncGenerator:
        """
        Generate SSE stream for customer.
        Yields notifications for the customer.
        """
        queue = self.get_customer_queue(customer_id)
        
        try:
            # Send connection confirmation
            yield {
                "event": "connected",
                "data": json.dumps({
                    "message": "Connected to notification stream",
                    "customer_id": customer_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            # Keep connection alive and send notifications
            while True:
                try:
                    # Wait for notification with timeout for keepalive
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Filter by salon_id if specified
                    if salon_id is None or notification.get('salon_id') == salon_id:
                        yield {
                            "event": "notification",
                            "data": json.dumps(notification)
                        }
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {
                        "event": "ping",
                        "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                    }
                    
        except asyncio.CancelledError:
            logger.info(f"Customer {customer_id} disconnected")
        finally:
            # Cleanup on disconnect
            if customer_id in self.customer_queues:
                del self.customer_queues[customer_id]
            if customer_id in self.active_connections['customers']:
                self.active_connections['customers'].remove(customer_id)
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "active_admin_connections": len(self.admin_queues),
            "active_customer_connections": len(self.customer_queues),
            "total_connections": len(self.admin_queues) + len(self.customer_queues),
            "admins": list(self.active_connections['admins']),
            "customers": list(self.active_connections['customers'])
        }


# Global notification manager instance
notification_manager = NotificationManager()
