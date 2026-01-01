"""
Notification Service - Handles Email, SMS, and Browser Push Notifications

Notification Priority Flow:
1. If user has browser push enabled -> Send push notification (preferred)
2. If no push subscription -> Fall back to email/SMS based on preference

Notification Types:
- BOOKING_CREATED: When a new booking is made
- BOOKING_REMINDER: Day-of reminder for appointments
- BOOKING_CANCELLED_BY_SALON: When salon cancels
- BOOKING_CANCELLED_BY_CUSTOMER: When customer cancels
- ORDER_PLACED: When product order is placed
- ORDER_STATUS_UPDATED: When order status changes
- SPECIAL_REQUEST_RECEIVED: When salon receives special request
- SPECIAL_REQUEST_QUOTED: When salon quotes a special request
- OFFSITE_BOOKING_QUOTED: When salon quotes offsite booking
"""

import os
import json
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException

# Email Configuration - from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@salon.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Salon Booking")

# SMS Configuration (Termii for Nigeria)
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "Salon")

# Web Push VAPID Keys
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "admin@salon.com")

# Platform base URLs
BACKOFFICE_URL = os.getenv("BACKOFFICE_URL", "http://localhost:3000")
CUSTOMER_APP_URL = os.getenv("CUSTOMER_APP_URL", "http://localhost:3001")


class NotificationType:
    """Notification type constants"""
    BOOKING_CREATED = "booking_created"
    BOOKING_REMINDER = "booking_reminder"
    BOOKING_CANCELLED_BY_SALON = "booking_cancelled_by_salon"
    BOOKING_CANCELLED_BY_CUSTOMER = "booking_cancelled_by_customer"
    BOOKING_COMPLETED = "booking_completed"
    ORDER_PLACED = "order_placed"
    ORDER_STATUS_UPDATED = "order_status_updated"
    SPECIAL_REQUEST_RECEIVED = "special_request_received"
    SPECIAL_REQUEST_QUOTED = "special_request_quoted"
    OFFSITE_BOOKING_QUOTED = "offsite_booking_quoted"
    OFFSITE_BOOKING_ACCEPTED = "offsite_booking_accepted"
    OFFSITE_BOOKING_REJECTED = "offsite_booking_rejected"


class NotificationChannel:
    """Notification channel constants"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    ALL = "all"


class NotificationService:
    """
    Centralized notification service for the salon platform.
    
    Priority: Push > Email > SMS
    If browser push is enabled, skip email/SMS to avoid notification spam.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== EMAIL METHODS ====================
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
        """
        Send an email notification.
        Returns True if successful, False otherwise.
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            print(f"[EMAIL] SMTP not configured. Would send to {to_email}: {subject}")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            
            # Attach both text and HTML versions
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
            
            print(f"[EMAIL] Sent to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"[EMAIL] Failed to send to {to_email}: {str(e)}")
            return False
    
    # ==================== SMS METHODS ====================
    
    def _send_sms(self, phone: str, message: str) -> bool:
        """
        Send an SMS notification using Termii API (popular in Nigeria).
        Returns True if successful, False otherwise.
        """
        if not SMS_API_KEY:
            print(f"[SMS] API not configured. Would send to {phone}: {message}")
            return False
        
        try:
            import requests
            
            url = "https://api.ng.termii.com/api/sms/send"
            payload = {
                "to": phone,
                "from": SMS_SENDER_ID,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": SMS_API_KEY
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"[SMS] Sent to {phone}")
                return True
            else:
                print(f"[SMS] Failed to send to {phone}: {response.text}")
                return False
        except Exception as e:
            print(f"[SMS] Failed to send to {phone}: {str(e)}")
            return False
    
    # ==================== PUSH NOTIFICATION METHODS ====================
    
    def _send_push(self, subscription_info: dict, title: str, body: str, data: dict = None, icon: str = None) -> bool:
        """
        Send a browser push notification.
        Returns True if successful, False otherwise.
        """
        if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
            print(f"[PUSH] VAPID keys not configured. Would push: {title}")
            return False
        
        try:
            payload = {
                "title": title,
                "body": body,
                "icon": icon or "/logo192.png",
                "badge": "/badge.png",
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{VAPID_CLAIMS_EMAIL}"
                }
            )
            
            print(f"[PUSH] Sent: {title}")
            return True
        except WebPushException as e:
            print(f"[PUSH] Failed: {str(e)}")
            # If subscription is expired/invalid, mark it for deletion
            if e.response and e.response.status_code in [404, 410]:
                return False
            return False
        except Exception as e:
            print(f"[PUSH] Failed: {str(e)}")
            return False
    
    # ==================== NOTIFICATION STORAGE ====================
    
    def _save_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        recipient_type: str,  # "salon", "customer", "user"
        recipient_id: int,
        salon_id: int = None,
        entity_type: str = None,
        entity_id: int = None,
        channels_sent: List[str] = None,
        extra_data: dict = None
    ):
        """Save notification to database for history/in-app display"""
        from app.models.models import Notification
        
        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            salon_id=salon_id,
            entity_type=entity_type,
            entity_id=entity_id,
            channels_sent=",".join(channels_sent) if channels_sent else None,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        
        self.db.add(notification)
        self.db.commit()
        
        return notification
    
    def _get_push_subscriptions(self, recipient_type: str, recipient_id: int) -> List[dict]:
        """Get active push subscriptions for a recipient"""
        from app.models.models import PushSubscription
        
        subscriptions = self.db.query(PushSubscription).filter(
            PushSubscription.recipient_type == recipient_type,
            PushSubscription.recipient_id == recipient_id,
            PushSubscription.is_active == 1
        ).all()
        
        return [
            {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh_key,
                    "auth": sub.auth_key
                }
            }
            for sub in subscriptions
        ]
    
    # ==================== HIGH-LEVEL NOTIFICATION METHODS ====================
    
    def notify(
        self,
        notification_type: str,
        title: str,
        message: str,
        recipient_type: str,
        recipient_id: int,
        email: str = None,
        phone: str = None,
        salon_id: int = None,
        entity_type: str = None,
        entity_id: int = None,
        extra_data: dict = None,
        email_html: str = None,
        url: str = None,
        force_channels: List[str] = None
    ) -> Dict[str, bool]:
        """
        Send notification through appropriate channels.
        
        Priority: Push > Email > SMS
        If push succeeds, skip email/SMS unless force_channels specified.
        
        Returns dict of channel -> success status
        """
        results = {}
        channels_sent = []
        
        # Get push subscriptions
        subscriptions = self._get_push_subscriptions(recipient_type, recipient_id)
        push_sent = False
        
        # Try push first (preferred)
        if subscriptions:
            push_data = {
                "type": notification_type,
                "url": url,
                "entity_type": entity_type,
                "entity_id": entity_id,
                **(extra_data or {})
            }
            
            for sub in subscriptions:
                if self._send_push(sub, title, message, push_data):
                    push_sent = True
                    results["push"] = True
                    channels_sent.append(NotificationChannel.PUSH)
                    break
        
        # If push failed or force_channels specified, try other channels
        should_email = (not push_sent or (force_channels and NotificationChannel.EMAIL in force_channels))
        should_sms = (not push_sent or (force_channels and NotificationChannel.SMS in force_channels))
        
        # Send email
        if should_email and email:
            html_content = email_html or self._create_email_html(title, message, url)
            if self._send_email(email, title, html_content, message):
                results["email"] = True
                channels_sent.append(NotificationChannel.EMAIL)
            else:
                results["email"] = False
        
        # Send SMS (only for critical notifications if push/email failed)
        critical_types = [
            NotificationType.BOOKING_REMINDER,
            NotificationType.BOOKING_CANCELLED_BY_SALON,
            NotificationType.BOOKING_CANCELLED_BY_CUSTOMER
        ]
        if should_sms and phone and notification_type in critical_types and not push_sent and not results.get("email"):
            if self._send_sms(phone, f"{title}: {message}"):
                results["sms"] = True
                channels_sent.append(NotificationChannel.SMS)
            else:
                results["sms"] = False
        
        # Save notification to database
        self._save_notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            salon_id=salon_id,
            entity_type=entity_type,
            entity_id=entity_id,
            channels_sent=channels_sent,
            extra_data=extra_data
        )
        
        return results
    
    def _create_email_html(self, title: str, message: str, url: str = None) -> str:
        """Create a simple HTML email template"""
        cta_button = ""
        if url:
            cta_button = f'''
            <p style="text-align: center; margin-top: 20px;">
                <a href="{url}" style="background-color: #1a1a1a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Details
                </a>
            </p>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 30px;">
                <h1 style="color: #1a1a1a; margin-bottom: 16px; font-size: 24px;">{title}</h1>
                <p style="color: #555; font-size: 16px; margin-bottom: 24px;">{message}</p>
                {cta_button}
            </div>
            <p style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
                This is an automated message from Salon Booking Platform.
            </p>
        </body>
        </html>
        '''
    
    # ==================== BOOKING NOTIFICATIONS ====================
    
    def notify_booking_created(self, appointment, salon, customer, service, sub_service=None):
        """
        Notify both salon and customer when a booking is created.
        """
        date_str = appointment.appointment_date.strftime("%A, %B %d, %Y at %I:%M %p")
        service_name = f"{service.name}"
        if sub_service:
            service_name += f" - {sub_service.name}"
        
        # Notify Salon
        salon_title = "New Booking Received! 📅"
        salon_message = f"{customer.name} has booked {service_name} for {date_str}"
        
        # Get salon admin user for notification
        from app.models.models import User
        salon_user = self.db.query(User).filter(
            User.salon_id == salon.id,
            User.is_admin == 1
        ).first()
        
        if salon_user:
            self.notify(
                notification_type=NotificationType.BOOKING_CREATED,
                title=salon_title,
                message=salon_message,
                recipient_type="user",
                recipient_id=salon_user.id,
                email=salon.email,
                phone=salon.phone,
                salon_id=salon.id,
                entity_type="appointment",
                entity_id=appointment.id,
                url=f"{BACKOFFICE_URL}/appointments",
                extra_data={
                    "customer_name": customer.name,
                    "service_name": service_name,
                    "appointment_date": date_str
                }
            )
        
        # Notify Customer
        customer_title = "Booking Confirmed! ✅"
        customer_message = f"Your appointment at {salon.name} for {service_name} is confirmed for {date_str}"
        
        self.notify(
            notification_type=NotificationType.BOOKING_CREATED,
            title=customer_title,
            message=customer_message,
            recipient_type="customer",
            recipient_id=customer.id,
            email=customer.email,
            phone=customer.phone,
            salon_id=salon.id,
            entity_type="appointment",
            entity_id=appointment.id,
            url=f"{CUSTOMER_APP_URL}/bookings",
            extra_data={
                "salon_name": salon.name,
                "service_name": service_name,
                "appointment_date": date_str
            }
        )
    
    def notify_booking_reminder(self, appointment, salon, customer, service, sub_service=None):
        """
        Day-of reminder for upcoming appointment.
        """
        time_str = appointment.appointment_date.strftime("%I:%M %p")
        service_name = f"{service.name}"
        if sub_service:
            service_name += f" - {sub_service.name}"
        
        # Notify Salon
        salon_title = "Appointment Today! ⏰"
        salon_message = f"Reminder: {customer.name} has an appointment for {service_name} at {time_str}"
        
        from app.models.models import User
        salon_user = self.db.query(User).filter(
            User.salon_id == salon.id,
            User.is_admin == 1
        ).first()
        
        if salon_user:
            self.notify(
                notification_type=NotificationType.BOOKING_REMINDER,
                title=salon_title,
                message=salon_message,
                recipient_type="user",
                recipient_id=salon_user.id,
                email=salon.email,
                phone=salon.phone,
                salon_id=salon.id,
                entity_type="appointment",
                entity_id=appointment.id
            )
        
        # Notify Customer
        customer_title = "Your Appointment is Today! ⏰"
        customer_message = f"Reminder: Your appointment at {salon.name} for {service_name} is today at {time_str}"
        
        self.notify(
            notification_type=NotificationType.BOOKING_REMINDER,
            title=customer_title,
            message=customer_message,
            recipient_type="customer",
            recipient_id=customer.id,
            email=customer.email,
            phone=customer.phone,
            salon_id=salon.id,
            entity_type="appointment",
            entity_id=appointment.id,
            url=f"{CUSTOMER_APP_URL}/bookings"
        )
    
    def notify_booking_cancelled_by_salon(self, appointment, salon, customer, service, reason: str = None):
        """
        Notify customer when salon cancels their booking.
        """
        date_str = appointment.appointment_date.strftime("%A, %B %d at %I:%M %p")
        
        title = "Appointment Cancelled 😔"
        message = f"Unfortunately, your appointment at {salon.name} for {date_str} has been cancelled."
        if reason:
            message += f" Reason: {reason}"
        message += " Please contact the salon to reschedule."
        
        self.notify(
            notification_type=NotificationType.BOOKING_CANCELLED_BY_SALON,
            title=title,
            message=message,
            recipient_type="customer",
            recipient_id=customer.id,
            email=customer.email,
            phone=customer.phone,
            salon_id=salon.id,
            entity_type="appointment",
            entity_id=appointment.id,
            url=f"{CUSTOMER_APP_URL}/salon/{salon.slug}",
            extra_data={"reason": reason}
        )
    
    def notify_booking_cancelled_by_customer(self, appointment, salon, customer, service):
        """
        Notify salon when customer cancels their booking.
        """
        date_str = appointment.appointment_date.strftime("%A, %B %d at %I:%M %p")
        
        title = "Booking Cancelled ❌"
        message = f"{customer.name} has cancelled their appointment for {service.name} on {date_str}"
        
        from app.models.models import User
        salon_user = self.db.query(User).filter(
            User.salon_id == salon.id,
            User.is_admin == 1
        ).first()
        
        if salon_user:
            self.notify(
                notification_type=NotificationType.BOOKING_CANCELLED_BY_CUSTOMER,
                title=title,
                message=message,
                recipient_type="user",
                recipient_id=salon_user.id,
                email=salon.email,
                phone=salon.phone,
                salon_id=salon.id,
                entity_type="appointment",
                entity_id=appointment.id,
                url=f"{BACKOFFICE_URL}/appointments"
            )
    
    # ==================== ORDER NOTIFICATIONS ====================
    
    def notify_order_placed(self, order, salon, items_summary: str):
        """
        Notify salon when a product order is placed.
        """
        customer_info = order.customer_name or (order.customer.name if order.customer else "A customer")
        total = order.total_amount / 100  # Convert from cents
        
        title = "New Order Received! 🛒"
        message = f"{customer_info} placed an order for ₦{total:,.2f}. Items: {items_summary}"
        
        from app.models.models import User
        salon_user = self.db.query(User).filter(
            User.salon_id == salon.id,
            User.is_admin == 1
        ).first()
        
        if salon_user:
            self.notify(
                notification_type=NotificationType.ORDER_PLACED,
                title=title,
                message=message,
                recipient_type="user",
                recipient_id=salon_user.id,
                email=salon.email,
                phone=salon.phone,
                salon_id=salon.id,
                entity_type="order",
                entity_id=order.id,
                url=f"{BACKOFFICE_URL}/orders",
                extra_data={
                    "order_number": order.order_number,
                    "total_amount": order.total_amount,
                    "customer_name": customer_info
                }
            )
        
        # Also notify customer
        if order.customer:
            customer_title = "Order Confirmed! 🎉"
            customer_message = f"Your order #{order.order_number} at {salon.name} has been placed successfully. Total: ₦{total:,.2f}"
            
            self.notify(
                notification_type=NotificationType.ORDER_PLACED,
                title=customer_title,
                message=customer_message,
                recipient_type="customer",
                recipient_id=order.customer.id,
                email=order.customer.email,
                phone=order.customer.phone,
                salon_id=salon.id,
                entity_type="order",
                entity_id=order.id,
                url=f"{CUSTOMER_APP_URL}/orders"
            )
    
    # ==================== SPECIAL REQUEST NOTIFICATIONS ====================
    
    def notify_special_request_received(self, request, salon, customer):
        """
        Notify salon when they receive a special request.
        """
        title = "New Special Request! ✨"
        message = f"{customer.name} has submitted a special request: {request.description[:100]}..."
        
        from app.models.models import User
        salon_user = self.db.query(User).filter(
            User.salon_id == salon.id,
            User.is_admin == 1
        ).first()
        
        if salon_user:
            self.notify(
                notification_type=NotificationType.SPECIAL_REQUEST_RECEIVED,
                title=title,
                message=message,
                recipient_type="user",
                recipient_id=salon_user.id,
                email=salon.email,
                salon_id=salon.id,
                entity_type="special_request",
                entity_id=request.id,
                url=f"{BACKOFFICE_URL}/special-requests"
            )
    
    def notify_special_request_quoted(self, request, salon, customer):
        """
        Notify customer when salon quotes their special request.
        """
        amount = request.quoted_amount / 100 if request.quoted_amount else 0
        
        title = f"Quote Received from {salon.name}! 💰"
        message = f"Your special request has been quoted at ₦{amount:,.2f}. {request.salon_notes or ''}"
        
        self.notify(
            notification_type=NotificationType.SPECIAL_REQUEST_QUOTED,
            title=title,
            message=message,
            recipient_type="customer",
            recipient_id=customer.id,
            email=customer.email,
            phone=customer.phone,
            salon_id=salon.id,
            entity_type="special_request",
            entity_id=request.id,
            url=f"{CUSTOMER_APP_URL}/requests"
        )
    
    # ==================== OFFSITE BOOKING NOTIFICATIONS ====================
    
    def notify_offsite_quoted(self, appointment, salon, customer, quote_amount: int, notes: str = None):
        """
        Notify customer when salon quotes their offsite booking request.
        """
        amount = quote_amount / 100
        date_str = appointment.appointment_date.strftime("%A, %B %d at %I:%M %p")
        
        title = f"Offsite Booking Quote from {salon.name}! 🚗"
        message = f"Your offsite booking for {date_str} has been quoted at ₦{amount:,.2f} extra charge."
        if notes:
            message += f" Notes: {notes}"
        
        self.notify(
            notification_type=NotificationType.OFFSITE_BOOKING_QUOTED,
            title=title,
            message=message,
            recipient_type="customer",
            recipient_id=customer.id,
            email=customer.email,
            phone=customer.phone,
            salon_id=salon.id,
            entity_type="appointment",
            entity_id=appointment.id,
            url=f"{CUSTOMER_APP_URL}/bookings"
        )


# ==================== SCHEDULER FOR REMINDERS ====================

def get_today_appointments(db: Session) -> List:
    """Get all appointments scheduled for today that need reminders"""
    from app.models.models import Appointment
    
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    appointments = db.query(Appointment).filter(
        Appointment.status == "scheduled",
        Appointment.appointment_date >= today,
        Appointment.appointment_date < tomorrow
    ).all()
    
    return appointments


def send_daily_reminders(db: Session):
    """
    Send reminder notifications for today's appointments.
    Should be called by a cron job or scheduler in the morning.
    """
    from app.models.models import Salon, Customer, Service, SubService, Notification
    
    service = NotificationService(db)
    appointments = get_today_appointments(db)
    
    sent_count = 0
    for appointment in appointments:
        # Check if reminder already sent today
        existing = db.query(Notification).filter(
            Notification.entity_type == "appointment",
            Notification.entity_id == appointment.id,
            Notification.notification_type == NotificationType.BOOKING_REMINDER,
            Notification.created_at >= datetime.utcnow().date()
        ).first()
        
        if existing:
            continue
        
        # Get related entities
        salon = db.query(Salon).filter(Salon.id == appointment.salon_id).first()
        customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
        service_obj = db.query(Service).filter(Service.id == appointment.service_id).first()
        sub_service = None
        if appointment.sub_service_id:
            sub_service = db.query(SubService).filter(SubService.id == appointment.sub_service_id).first()
        
        if salon and customer and service_obj:
            service.notify_booking_reminder(appointment, salon, customer, service_obj, sub_service)
            sent_count += 1
    
    print(f"[SCHEDULER] Sent {sent_count} reminder notifications")
    return sent_count
