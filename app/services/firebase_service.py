"""
Firebase Cloud Messaging Service

Handles sending push notifications to mobile devices via FCM.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session

from app.models.models import MobileDeviceToken

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Service for sending Firebase Cloud Messaging notifications.
    
    Requires:
    - FIREBASE_SERVER_KEY: Legacy server key from Firebase Console
      OR
    - GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON file
    """
    
    FCM_LEGACY_URL = "https://fcm.googleapis.com/fcm/send"
    FCM_V1_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    def __init__(self):
        self.server_key = os.getenv("FIREBASE_SERVER_KEY")
        self.project_id = os.getenv("FIREBASE_PROJECT_ID")
        
    def is_configured(self) -> bool:
        """Check if Firebase is properly configured."""
        return bool(self.server_key)
    
    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None
    ) -> bool:
        """
        Send a push notification to a single device token.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body text
            data: Optional data payload (for app handling)
            image: Optional image URL for rich notifications
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_configured():
            logger.warning("Firebase not configured - skipping notification")
            return False
        
        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": data or {}
        }
        
        if image:
            payload["notification"]["image"] = image
        
        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.FCM_LEGACY_URL,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", 0) > 0:
                        logger.info(f"FCM notification sent successfully to token")
                        return True
                    else:
                        logger.warning(f"FCM send failed: {result}")
                        return False
                else:
                    logger.error(f"FCM request failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending FCM notification: {e}")
            return False
    
    async def send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Send a push notification to multiple device tokens.
        
        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body text
            data: Optional data payload
            image: Optional image URL
            
        Returns:
            Dict with success and failure counts
        """
        if not self.is_configured():
            logger.warning("Firebase not configured - skipping notifications")
            return {"success": 0, "failure": len(tokens)}
        
        if not tokens:
            return {"success": 0, "failure": 0}
        
        # FCM supports up to 500 tokens per request
        batch_size = 500
        total_success = 0
        total_failure = 0
        
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i + batch_size]
            
            payload = {
                "registration_ids": batch,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": data or {}
            }
            
            if image:
                payload["notification"]["image"] = image
            
            headers = {
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.FCM_LEGACY_URL,
                        json=payload,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        total_success += result.get("success", 0)
                        total_failure += result.get("failure", 0)
                    else:
                        total_failure += len(batch)
                        logger.error(f"FCM batch request failed: {response.status_code}")
                        
            except Exception as e:
                total_failure += len(batch)
                logger.error(f"Error sending FCM batch: {e}")
        
        return {"success": total_success, "failure": total_failure}
    
    async def send_to_user(
        self,
        db: Session,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Send notification to all devices registered to a salon admin user.
        """
        tokens = db.query(MobileDeviceToken).filter(
            MobileDeviceToken.recipient_type == "user",
            MobileDeviceToken.recipient_id == user_id,
            MobileDeviceToken.is_active == 1
        ).all()
        
        if not tokens:
            return {"success": 0, "failure": 0}
        
        token_list = [t.fcm_token for t in tokens]
        return await self.send_to_tokens(token_list, title, body, data, image)
    
    async def send_to_customer(
        self,
        db: Session,
        customer_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Send notification to all devices registered to a customer.
        """
        tokens = db.query(MobileDeviceToken).filter(
            MobileDeviceToken.recipient_type == "customer",
            MobileDeviceToken.recipient_id == customer_id,
            MobileDeviceToken.is_active == 1
        ).all()
        
        if not tokens:
            return {"success": 0, "failure": 0}
        
        token_list = [t.fcm_token for t in tokens]
        return await self.send_to_tokens(token_list, title, body, data, image)
    
    async def send_to_salon_admins(
        self,
        db: Session,
        salon_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Send notification to all admins of a salon.
        """
        from app.models.models import User
        
        # Get all users for this salon
        users = db.query(User).filter(User.salon_id == salon_id).all()
        
        if not users:
            return {"success": 0, "failure": 0}
        
        user_ids = [u.id for u in users]
        
        tokens = db.query(MobileDeviceToken).filter(
            MobileDeviceToken.recipient_type == "user",
            MobileDeviceToken.recipient_id.in_(user_ids),
            MobileDeviceToken.is_active == 1
        ).all()
        
        if not tokens:
            return {"success": 0, "failure": 0}
        
        token_list = [t.fcm_token for t in tokens]
        return await self.send_to_tokens(token_list, title, body, data, image)


# Global instance
firebase_service = FirebaseService()


# Convenience functions
async def send_push_notification(
    db: Session,
    recipient_type: str,
    recipient_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    image: Optional[str] = None
) -> Dict[str, int]:
    """
    Send push notification to a recipient.
    
    Args:
        db: Database session
        recipient_type: "user" or "customer"
        recipient_id: User or Customer ID
        title: Notification title
        body: Notification body
        data: Optional data payload
        image: Optional image URL
    """
    if recipient_type == "user":
        return await firebase_service.send_to_user(db, recipient_id, title, body, data, image)
    elif recipient_type == "customer":
        return await firebase_service.send_to_customer(db, recipient_id, title, body, data, image)
    else:
        logger.warning(f"Unknown recipient type: {recipient_type}")
        return {"success": 0, "failure": 0}
