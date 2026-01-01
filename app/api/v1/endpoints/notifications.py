"""
Notifications API Endpoints

Handles:
- Push subscription management (subscribe/unsubscribe)
- Notification listing and management
- Notification preferences
- VAPID public key for client
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime
import os

from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_customer
from app.models.models import (
    Notification, PushSubscription, NotificationPreference, User, Customer,
    MobileDeviceToken
)
from app.schemas.schemas import (
    PushSubscriptionCreate, PushSubscriptionResponse,
    NotificationResponse, NotificationListResponse,
    NotificationPreferenceUpdate, NotificationPreferenceResponse,
    MarkNotificationsRead, VapidPublicKeyResponse
)

router = APIRouter()


# ==================== VAPID KEY ====================

@router.get("/vapid-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key():
    """
    Get VAPID public key for browser push notification subscription.
    Client uses this to subscribe to push notifications.
    """
    public_key = os.getenv("VAPID_PUBLIC_KEY", "")
    if not public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured"
        )
    return {"public_key": public_key}


# ==================== PUSH SUBSCRIPTIONS (Salon Admin) ====================

@router.post("/push/subscribe", response_model=PushSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_push_admin(
    subscription: PushSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Subscribe salon admin to browser push notifications.
    """
    # Check if subscription already exists
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == subscription.endpoint
    ).first()
    
    if existing:
        # Update existing subscription
        existing.p256dh_key = subscription.p256dh_key
        existing.auth_key = subscription.auth_key
        existing.device_name = subscription.device_name
        existing.user_agent = request.headers.get("user-agent")
        existing.is_active = 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new subscription
    push_sub = PushSubscription(
        recipient_type="user",
        recipient_id=current_user.id,
        endpoint=subscription.endpoint,
        p256dh_key=subscription.p256dh_key,
        auth_key=subscription.auth_key,
        device_name=subscription.device_name,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(push_sub)
    db.commit()
    db.refresh(push_sub)
    
    return push_sub


@router.delete("/push/unsubscribe")
async def unsubscribe_push_admin(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unsubscribe from browser push notifications.
    """
    subscription = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint,
        PushSubscription.recipient_type == "user",
        PushSubscription.recipient_id == current_user.id
    ).first()
    
    if subscription:
        subscription.is_active = 0
        db.commit()
    
    return {"message": "Unsubscribed successfully"}


@router.get("/push/subscriptions", response_model=List[PushSubscriptionResponse])
async def list_push_subscriptions_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all push subscriptions for the current admin user.
    """
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.recipient_type == "user",
        PushSubscription.recipient_id == current_user.id,
        PushSubscription.is_active == 1
    ).all()
    
    return subscriptions


# ==================== PUSH SUBSCRIPTIONS (Customer) ====================

@router.post("/customer/push/subscribe", response_model=PushSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_push_customer(
    subscription: PushSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Subscribe customer to browser push notifications.
    """
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == subscription.endpoint
    ).first()
    
    if existing:
        existing.p256dh_key = subscription.p256dh_key
        existing.auth_key = subscription.auth_key
        existing.device_name = subscription.device_name
        existing.user_agent = request.headers.get("user-agent")
        existing.is_active = 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    push_sub = PushSubscription(
        recipient_type="customer",
        recipient_id=current_customer.id,
        endpoint=subscription.endpoint,
        p256dh_key=subscription.p256dh_key,
        auth_key=subscription.auth_key,
        device_name=subscription.device_name,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(push_sub)
    db.commit()
    db.refresh(push_sub)
    
    return push_sub


@router.delete("/customer/push/unsubscribe")
async def unsubscribe_push_customer(
    endpoint: str,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Unsubscribe customer from browser push notifications.
    """
    subscription = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint,
        PushSubscription.recipient_type == "customer",
        PushSubscription.recipient_id == current_customer.id
    ).first()
    
    if subscription:
        subscription.is_active = 0
        db.commit()
    
    return {"message": "Unsubscribed successfully"}


# ==================== NOTIFICATIONS (Salon Admin) ====================

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get notifications for salon admin.
    Returns paginated list with unread count.
    """
    query = db.query(Notification).filter(
        Notification.recipient_type == "user",
        Notification.recipient_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == 0)
    
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    
    # Get counts
    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.recipient_type == "user",
        Notification.recipient_id == current_user.id,
        Notification.is_read == 0
    ).count()
    
    # Get paginated results
    notifications = query.order_by(desc(Notification.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.post("/mark-read")
async def mark_notifications_read(
    data: MarkNotificationsRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Mark specific notifications as read.
    """
    db.query(Notification).filter(
        Notification.id.in_(data.notification_ids),
        Notification.recipient_type == "user",
        Notification.recipient_id == current_user.id
    ).update({
        "is_read": 1,
        "read_at": datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {len(data.notification_ids)} notifications as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Mark all notifications as read.
    """
    updated = db.query(Notification).filter(
        Notification.recipient_type == "user",
        Notification.recipient_id == current_user.id,
        Notification.is_read == 0
    ).update({
        "is_read": 1,
        "read_at": datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {updated} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a specific notification.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_type == "user",
        Notification.recipient_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}


# ==================== NOTIFICATIONS (Customer) ====================

@router.get("/customer", response_model=NotificationListResponse)
async def get_customer_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get notifications for customer.
    """
    query = db.query(Notification).filter(
        Notification.recipient_type == "customer",
        Notification.recipient_id == current_customer.id
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == 0)
    
    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.recipient_type == "customer",
        Notification.recipient_id == current_customer.id,
        Notification.is_read == 0
    ).count()
    
    notifications = query.order_by(desc(Notification.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.post("/customer/mark-read")
async def mark_customer_notifications_read(
    data: MarkNotificationsRead,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Mark customer notifications as read.
    """
    db.query(Notification).filter(
        Notification.id.in_(data.notification_ids),
        Notification.recipient_type == "customer",
        Notification.recipient_id == current_customer.id
    ).update({
        "is_read": 1,
        "read_at": datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {len(data.notification_ids)} notifications as read"}


# ==================== NOTIFICATION PREFERENCES ====================

@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get notification preferences for salon admin.
    """
    preferences = db.query(NotificationPreference).filter(
        NotificationPreference.recipient_type == "user",
        NotificationPreference.recipient_id == current_user.id
    ).all()
    
    return preferences


@router.post("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update notification preferences for salon admin.
    """
    existing = db.query(NotificationPreference).filter(
        NotificationPreference.recipient_type == "user",
        NotificationPreference.recipient_id == current_user.id,
        NotificationPreference.notification_type == data.notification_type
    ).first()
    
    if existing:
        existing.email_enabled = data.email_enabled
        existing.sms_enabled = data.sms_enabled
        existing.push_enabled = data.push_enabled
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    preference = NotificationPreference(
        recipient_type="user",
        recipient_id=current_user.id,
        notification_type=data.notification_type,
        email_enabled=data.email_enabled,
        sms_enabled=data.sms_enabled,
        push_enabled=data.push_enabled
    )
    
    db.add(preference)
    db.commit()
    db.refresh(preference)
    
    return preference


# ==================== SCHEDULER ENDPOINT (for cron) ====================

@router.post("/send-daily-reminders")
async def trigger_daily_reminders(
    api_key: str = Query(..., description="Secret API key for scheduler"),
    db: Session = Depends(get_db)
):
    """
    Trigger daily reminder notifications.
    Should be called by a cron job or scheduler.
    Requires API key for security.
    """
    expected_key = os.getenv("SCHEDULER_API_KEY", "")
    if not expected_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    from app.services.notification_service import send_daily_reminders
    
    count = send_daily_reminders(db)
    
    return {"message": f"Sent {count} reminder notifications"}


# ==================== MOBILE DEVICE TOKENS (FCM) ====================

@router.post("/mobile/register", status_code=status.HTTP_201_CREATED)
async def register_mobile_device_admin(
    fcm_token: str,
    platform: str,  # "ios" or "android"
    device_name: Optional[str] = None,
    device_model: Optional[str] = None,
    app_version: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Register a mobile device for push notifications (Salon Admin).
    Used for iOS/Android app push notifications via Firebase Cloud Messaging.
    """
    if platform not in ["ios", "android"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'ios' or 'android'"
        )
    
    # Check if token already exists
    existing = db.query(MobileDeviceToken).filter(
        MobileDeviceToken.fcm_token == fcm_token
    ).first()
    
    if existing:
        # Update existing token
        existing.recipient_type = "user"
        existing.recipient_id = current_user.id
        existing.platform = platform
        existing.device_name = device_name
        existing.device_model = device_model
        existing.app_version = app_version
        existing.is_active = 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return {
            "message": "Device token updated successfully",
            "token_id": existing.id
        }
    
    # Create new token
    device_token = MobileDeviceToken(
        recipient_type="user",
        recipient_id=current_user.id,
        fcm_token=fcm_token,
        platform=platform,
        device_name=device_name,
        device_model=device_model,
        app_version=app_version
    )
    
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    
    return {
        "message": "Device registered successfully",
        "token_id": device_token.id
    }


@router.delete("/mobile/unregister")
async def unregister_mobile_device_admin(
    fcm_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unregister a mobile device from push notifications (Salon Admin).
    """
    token = db.query(MobileDeviceToken).filter(
        MobileDeviceToken.fcm_token == fcm_token,
        MobileDeviceToken.recipient_type == "user",
        MobileDeviceToken.recipient_id == current_user.id
    ).first()
    
    if token:
        token.is_active = 0
        db.commit()
    
    return {"message": "Device unregistered successfully"}


@router.post("/customer/mobile/register", status_code=status.HTTP_201_CREATED)
async def register_mobile_device_customer(
    fcm_token: str,
    platform: str,  # "ios" or "android"
    device_name: Optional[str] = None,
    device_model: Optional[str] = None,
    app_version: Optional[str] = None,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Register a mobile device for push notifications (Customer).
    Used for iOS/Android app push notifications via Firebase Cloud Messaging.
    """
    if platform not in ["ios", "android"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'ios' or 'android'"
        )
    
    # Check if token already exists
    existing = db.query(MobileDeviceToken).filter(
        MobileDeviceToken.fcm_token == fcm_token
    ).first()
    
    if existing:
        # Update existing token
        existing.recipient_type = "customer"
        existing.recipient_id = current_customer.id
        existing.platform = platform
        existing.device_name = device_name
        existing.device_model = device_model
        existing.app_version = app_version
        existing.is_active = 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return {
            "message": "Device token updated successfully",
            "token_id": existing.id
        }
    
    # Create new token
    device_token = MobileDeviceToken(
        recipient_type="customer",
        recipient_id=current_customer.id,
        fcm_token=fcm_token,
        platform=platform,
        device_name=device_name,
        device_model=device_model,
        app_version=app_version
    )
    
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    
    return {
        "message": "Device registered successfully",
        "token_id": device_token.id
    }


@router.delete("/customer/mobile/unregister")
async def unregister_mobile_device_customer(
    fcm_token: str,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Unregister a mobile device from push notifications (Customer).
    """
    token = db.query(MobileDeviceToken).filter(
        MobileDeviceToken.fcm_token == fcm_token,
        MobileDeviceToken.recipient_type == "customer",
        MobileDeviceToken.recipient_id == current_customer.id
    ).first()
    
    if token:
        token.is_active = 0
        db.commit()
    
    return {"message": "Device unregistered successfully"}

