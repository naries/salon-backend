from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Time, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, time
from uuid import uuid4
from app.core.database import Base


# ==================== NOTIFICATION MODELS ====================

class Notification(Base):
    """
    Stored notifications for in-app display and history.
    Each notification represents a message sent to a recipient.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, nullable=False, index=True)  # booking_created, order_placed, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Recipient information
    recipient_type = Column(String, nullable=False)  # "salon", "customer", "user"
    recipient_id = Column(Integer, nullable=False, index=True)
    
    # Related entities
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type = Column(String, nullable=True)  # appointment, order, special_request, etc.
    entity_id = Column(Integer, nullable=True)
    
    # Delivery tracking
    channels_sent = Column(String, nullable=True)  # Comma-separated: "push,email,sms"
    
    # Read status
    is_read = Column(Integer, default=0)  # 0 = unread, 1 = read
    read_at = Column(DateTime, nullable=True)
    
    # Additional data
    extra_data = Column(Text, nullable=True)  # JSON string for additional context
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class MobileDeviceToken(Base):
    """
    Mobile app push notification tokens (FCM).
    Stores FCM tokens for iOS and Android devices.
    """
    __tablename__ = "mobile_device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who this token belongs to
    recipient_type = Column(String, nullable=False)  # "user" (salon admin) or "customer"
    recipient_id = Column(Integer, nullable=False, index=True)
    
    # FCM token
    fcm_token = Column(String, nullable=False, unique=True)
    
    # Device info
    platform = Column(String, nullable=False)  # "ios" or "android"
    device_name = Column(String, nullable=True)
    device_model = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    
    # Status
    is_active = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FAQ(Base):
    """
    Frequently Asked Questions - managed by superadmin.
    """
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerSupportMessage(Base):
    """
    Customer support messages - customers can send messages and receive responses.
    """
    __tablename__ = "customer_support_messages"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, resolved
    admin_response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    responded_by = Column(Integer, nullable=True)  # User ID of admin who responded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="support_messages")


class PushSubscription(Base):
    """
    Browser push notification subscriptions.
    Stores the subscription info needed to send web push notifications.
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who this subscription belongs to
    recipient_type = Column(String, nullable=False)  # "user" (salon admin) or "customer"
    recipient_id = Column(Integer, nullable=False, index=True)
    
    # Push subscription data from browser
    endpoint = Column(String, nullable=False, unique=True)
    p256dh_key = Column(String, nullable=False)  # Public key
    auth_key = Column(String, nullable=False)  # Auth secret
    
    # Device info (for managing multiple devices)
    device_name = Column(String, nullable=True)  # User-friendly device name
    user_agent = Column(String, nullable=True)  # Browser/device info
    
    # Status
    is_active = Column(Integer, default=1)  # 1 = active, 0 = expired/unsubscribed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('recipient_type', 'recipient_id', 'endpoint', name='uq_push_subscription'),
    )


class NotificationPreference(Base):
    """
    User/Customer preferences for notification channels.
    Allows users to opt-in/out of specific notification types and channels.
    """
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who this preference belongs to
    recipient_type = Column(String, nullable=False)  # "user" or "customer"
    recipient_id = Column(Integer, nullable=False, index=True)
    
    # Notification type (or "all" for global preference)
    notification_type = Column(String, nullable=False, default="all")
    
    # Channel preferences
    email_enabled = Column(Integer, default=1)  # 0 = disabled, 1 = enabled
    sms_enabled = Column(Integer, default=1)
    push_enabled = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('recipient_type', 'recipient_id', 'notification_type', name='uq_notification_pref'),
    )


# ==================== EXISTING MODELS ====================

class SuperadminSettings(Base):
    __tablename__ = "superadmin_settings"

    id = Column(Integer, primary_key=True, index=True)
    default_logo_icon = Column(String, default="scissors")  # Default icon for new salons
    default_opening_hour = Column(Integer, default=9)  # Default opening hour
    default_closing_hour = Column(Integer, default=18)  # Default closing hour
    default_max_concurrent_slots = Column(Integer, default=2)  # Default booking slots
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CloudFile(Base):
    __tablename__ = "cloud_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # GCS path
    file_type = Column(String, nullable=False)  # MIME type
    file_size = Column(Integer)  # Size in bytes
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    salons = relationship("Salon", back_populates="logo_file")


class MediaUpload(Base):
    """
    Track media uploads to Cloudinary.
    Files are uploaded synchronously and records include URLs immediately.
    """
    __tablename__ = "media_uploads"

    id = Column(Integer, primary_key=True, index=True)
    
    # File metadata
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # MIME type
    file_size = Column(Integer, nullable=False)  # Size in bytes
    
    # Upload status
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # GCS details (populated after upload)
    gcs_path = Column(String, nullable=True)  # GCS object path
    public_url = Column(String, nullable=True)  # Public URL if accessible
    bucket_name = Column(String, nullable=True)
    
    # Organization
    folder = Column(String, default="uploads")  # Folder/category for organizing files
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processing_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    salon = relationship("Salon", foreign_keys=[salon_id])


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # "Free Basic", "Standard", "Premium"
    description = Column(Text)
    price = Column(Integer, default=0)  # Deprecated: Use monthly_price instead
    monthly_price = Column(Integer, default=0)  # Monthly price in cents (0 for free plan)
    yearly_price = Column(Integer, default=0)  # Yearly price in cents (0 for free plan)
    discount_percentage = Column(Float, default=0)  # Discount percentage for yearly plans
    features = Column(Text)  # JSON string of features
    max_services = Column(Integer, default=5)  # Maximum services allowed
    max_staff = Column(Integer, default=1)  # Maximum staff members
    max_appointments_per_month = Column(Integer, default=0)  # 0 for unlimited
    max_customers = Column(Integer, default=0)  # 0 for unlimited
    max_concurrent_slots = Column(Integer, default=1)  # Maximum concurrent time slots
    has_analytics = Column(Integer, default=0)  # 1 for yes, 0 for no
    has_advanced_reporting = Column(Integer, default=0)  # 1 for yes, 0 for no
    has_custom_branding = Column(Integer, default=0)  # 1 for yes, 0 for no
    has_priority_support = Column(Integer, default=0)  # 1 for yes, 0 for no
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    salons = relationship("Salon", back_populates="plan")


class ServiceTemplate(Base):
    __tablename__ = "service_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # "Hair", "Nails", "Spa", "Beauty", etc.
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Salon(Base):
    __tablename__ = "salons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)  # Unique identifier for salon URL
    address = Column(String)
    phone = Column(String)
    email = Column(String, unique=True, index=True)
    latitude = Column(Float, nullable=True)  # GPS latitude for location-based features
    longitude = Column(Float, nullable=True)  # GPS longitude for location-based features
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    billing_cycle = Column(String, default="monthly")  # "monthly" or "yearly"
    auto_debit = Column(Integer, default=0)  # 0 for manual, 1 for auto-debit
    opening_hour = Column(Integer, default=9)  # Opening hour (0-23), default 9 AM
    closing_hour = Column(Integer, default=18)  # Closing hour (0-23), default 6 PM
    max_concurrent_slots = Column(Integer, default=3)  # Maximum number of parallel booking slots
    theme_name = Column(String, default="purple")  # Selected theme for backoffice UI
    logo_type = Column(String, default="icon")  # "icon" for predefined icon, "upload" for uploaded file
    logo_icon_name = Column(String, default="scissors")  # Name of predefined icon
    logo_file_id = Column(Integer, ForeignKey("cloud_files.id", ondelete="SET NULL"), nullable=True)
    layout_pattern = Column(String, default="classic")  # Web client layout: classic, modern, minimal, compact, elegant
    client_theme_name = Column(String, default="ocean")  # Web client theme (different from backoffice)
    custom_css = Column(Text, nullable=True)  # Custom CSS for advanced customization
    primary_color = Column(String, nullable=True)  # Primary color override (hex)
    accent_color = Column(String, nullable=True)  # Accent color override (hex)
    about_us = Column(Text, nullable=True)  # About Us text displayed on web client
    default_completion_message = Column(Text, default="Thank you for visiting! We hope you enjoyed your service. See you again soon!")  # Default message when completing appointments
    default_cancellation_message = Column(Text, default="We're sorry to inform you that your appointment has been cancelled. Please contact us to reschedule.")  # Default message when cancelling appointments
    
    # Social media links
    instagram_url = Column(String, nullable=True)  # Instagram profile URL
    tiktok_url = Column(String, nullable=True)  # TikTok profile URL
    facebook_url = Column(String, nullable=True)  # Facebook page URL
    
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plan = relationship("Plan", back_populates="salons")
    users = relationship("User", back_populates="salon")
    appointments = relationship("Appointment", back_populates="salon")
    services = relationship("Service", back_populates="salon")
    logo_file = relationship("CloudFile", back_populates="salons", foreign_keys=[logo_file_id])
    salon_customers = relationship("SalonCustomer", back_populates="salon", cascade="all, delete-orphan")
    favorited_by = relationship("CustomerFavoriteSalon", back_populates="salon", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_admin = Column(Integer, default=1)  # 1 for salon admin
    is_superadmin = Column(Integer, default=0)  # 1 for superadmin (platform admin)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=True)  # NULL for superadmins
    theme_name = Column(String, default="purple")  # Selected theme for backoffice UI
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", back_populates="users")


class Customer(Base):
    """Platform-wide customer - signs up once, can book/purchase from any salon"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))  # UUID for secure identification
    # Legacy field - kept for backward compatibility, will be deprecated
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=True)
    
    # Customer profile
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    hashed_password = Column(String, nullable=True)  # For customer authentication
    
    # Platform fields
    is_verified = Column(Integer, default=0)  # 1 if email verified, 0 otherwise
    platform_joined_at = Column(DateTime, default=datetime.utcnow)  # When they joined the platform
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="customers")  # Legacy - kept for backward compatibility
    appointments = relationship("Appointment", back_populates="customer")
    salon_customers = relationship("SalonCustomer", back_populates="customer", cascade="all, delete-orphan")
    favorite_salons = relationship("CustomerFavoriteSalon", back_populates="customer", cascade="all, delete-orphan")
    support_messages = relationship("CustomerSupportMessage", back_populates="customer", cascade="all, delete-orphan")


class CustomerFavoriteSalon(Base):
    """Stores customer's favorite salons"""
    __tablename__ = "customer_favorite_salons"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="favorite_salons")
    salon = relationship("Salon", back_populates="favorited_by")


class SalonCustomer(Base):
    """
    Junction table linking platform customers to salons they've interacted with.
    A customer becomes a salon's customer when they:
    1. Book an appointment with the salon
    2. Purchase products from the salon
    """
    __tablename__ = "salon_customers"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # How they became a customer of this salon
    source = Column(String, default="appointment")  # "appointment", "purchase", "manual"
    
    # Salon-specific customer data
    notes = Column(Text, nullable=True)  # Salon's notes about this customer
    loyalty_points = Column(Integer, default=0)  # Loyalty points with this salon
    total_spent = Column(Integer, default=0)  # Total spent at this salon in cents
    total_appointments = Column(Integer, default=0)  # Total appointments with this salon
    is_favorite = Column(Integer, default=0)  # 1 if salon marked as favorite customer
    
    first_interaction_at = Column(DateTime, default=datetime.utcnow)  # When they first interacted with salon
    last_interaction_at = Column(DateTime, default=datetime.utcnow)  # Last interaction
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", back_populates="salon_customers")
    customer = relationship("Customer", back_populates="salon_customers")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    service_template_id = Column(Integer, ForeignKey("service_templates.id"), nullable=True)  # NULL if custom service
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Integer)  # Price in cents (per hour or flat rate)
    duration_minutes = Column(Integer)  # Duration in minutes
    is_custom = Column(Integer, default=0)  # 1 if custom service created by salon, 0 if from template
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
    sub_services = relationship("SubService", back_populates="service", cascade="all, delete-orphan")
    service_template = relationship("ServiceTemplate", backref="services")


class SubService(Base):
    __tablename__ = "sub_services"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    pricing_type = Column(String, default="hourly")  # "hourly" or "one_time"
    booking_type = Column(String, default="both")  # "timed", "full_day", or "both"
    hourly_rate = Column(Integer, nullable=False)  # Price per hour in cents (or total price for one_time)
    min_hours = Column(Integer, default=1)  # Minimum hours required (only for hourly)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship("Service", back_populates="sub_services")
    appointments = relationship("Appointment", back_populates="sub_service")
    suggested_products = relationship("SubServiceProduct", back_populates="sub_service", cascade="all, delete-orphan")


class SubServiceProduct(Base):
    __tablename__ = "sub_service_products"

    id = Column(Integer, primary_key=True, index=True)
    sub_service_id = Column(Integer, ForeignKey("sub_services.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sub_service = relationship("SubService", back_populates="suggested_products")
    product = relationship("Product")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    sub_service_id = Column(Integer, ForeignKey("sub_services.id"), nullable=True)  # Optional sub-service
    appointment_date = Column(DateTime, nullable=False)
    hours = Column(Float, default=1.0)  # Number of hours for sub-service billing
    slot_number = Column(Integer, nullable=False, default=1)  # Which slot/calendar this appointment occupies
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled, pending_review, approved, rejected
    status_message = Column(Text, nullable=True)  # Message from salon when completing/cancelling
    notes = Column(Text)
    
    # Off-site booking fields
    is_offsite = Column(Integer, default=0)  # 1 for off-site, 0 for on-site
    offsite_location = Column(Text, nullable=True)  # Customer's location for off-site service
    offsite_extra_charge = Column(Integer, nullable=True)  # Extra charge in cents quoted by salon
    offsite_response = Column(Text, nullable=True)  # Salon's response/notes for the off-site request
    offsite_status = Column(String, nullable=True)  # pending, quoted, accepted, rejected
    offsite_responded_at = Column(DateTime, nullable=True)  # When salon responded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    sub_service = relationship("SubService", back_populates="appointments")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(String, default="active")  # active, cancelled, expired, trial
    billing_cycle = Column(String, default="monthly")  # monthly or yearly
    amount = Column(Integer, nullable=False)  # Amount in cents
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)  # When subscription expires
    auto_renew = Column(Integer, default=1)  # 1 for auto-renew, 0 for manual
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", foreign_keys=[salon_id])
    plan = relationship("Plan", foreign_keys=[plan_id])


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=True)
    action = Column(String, nullable=False)  # created, updated, deleted, login, logout, etc.
    entity_type = Column(String, nullable=True)  # salon, user, appointment, service, customer, plan, etc.
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity
    description = Column(Text, nullable=True)  # Human-readable description
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON string for additional data (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    salon = relationship("Salon", foreign_keys=[salon_id])


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="product_categories")
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)  # Price in cents
    discount_percentage = Column(Float, default=0)  # Discount percentage (0-100)
    quantity = Column(Integer, default=0)  # Available quantity
    image_file_id = Column(Integer, ForeignKey("cloud_files.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive (soft delete)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="products")
    category = relationship("ProductCategory", back_populates="products")
    image_file = relationship("CloudFile", foreign_keys=[image_file_id])
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class ProductImage(Base):
    """Model for storing multiple images per product"""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Integer, ForeignKey("cloud_files.id", ondelete="SET NULL"), nullable=True)
    display_order = Column(Integer, default=0)  # Order in which images are displayed
    is_primary = Column(Integer, default=0)  # 1 if this is the primary/featured image
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="images")
    file = relationship("CloudFile")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", backref="carts")
    salon = relationship("Salon", backref="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)  # Allow null for public orders
    order_number = Column(String, unique=True, nullable=False, index=True)
    total_amount = Column(Integer, nullable=False)  # Total in cents
    status = Column(String, default="pending")  # pending, paid, failed, cancelled
    payment_method = Column(String)  # paystack, flutterwave
    payment_reference = Column(String, unique=True, index=True)  # Payment gateway reference
    payment_data = Column(Text)  # JSON string for payment gateway response
    
    # Customer information for public orders (when customer_id is null)
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    delivery_address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="orders")
    customer = relationship("Customer", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Nullable for pack orders
    pack_id = Column(Integer, ForeignKey("packs.id"), nullable=True)  # For pack orders
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Integer, nullable=False)  # Price in cents at time of purchase
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    pack = relationship("Pack", back_populates="order_items")


class Pack(Base):
    __tablename__ = "packs"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    custom_price = Column(Integer, nullable=True)  # Custom price in cents (overrides calculated price)
    discount_percentage = Column(Float, default=0)  # Discount percentage (0-100)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="packs")
    pack_products = relationship("PackProduct", back_populates="pack", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="pack")


class PackProduct(Base):
    __tablename__ = "pack_products"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("packs.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)  # Number of this product in the pack
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pack = relationship("Pack", back_populates="pack_products")
    product = relationship("Product", backref="pack_products")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False, unique=True)
    balance = Column(Integer, default=0, nullable=False)  # Balance in cents
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Link to order if payment-related
    amount = Column(Integer, nullable=False)  # Amount in cents
    type = Column(String, nullable=False)  # "credit" or "debit"
    status = Column(String, default="pending")  # pending, completed, failed
    payment_reference = Column(String, nullable=True, index=True)  # Payment gateway reference
    description = Column(Text, nullable=True)  # Transaction description
    transaction_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    order = relationship("Order", backref="wallet_transaction")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    bank_code = Column(String, nullable=True)  # Nigerian bank code
    is_default = Column(Integer, default=0)  # 0 or 1
    is_verified = Column(Integer, default=0)  # 0 or 1, verified by admin or payment gateway
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="bank_accounts")
    withdrawals = relationship("Withdrawal", back_populates="bank_account")


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in cents
    status = Column(String, default="pending")  # pending, approved, rejected, completed, failed
    reference = Column(String, unique=True, nullable=False, index=True)  # Unique withdrawal reference
    notes = Column(Text, nullable=True)  # Notes from salon
    admin_notes = Column(Text, nullable=True)  # Notes from superadmin
    transaction_reference = Column(String, nullable=True)  # Payment gateway transaction reference
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Superadmin who processed
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("Wallet", backref="withdrawals")
    bank_account = relationship("BankAccount", back_populates="withdrawals")
    processor = relationship("User", foreign_keys=[processed_by], backref="processed_withdrawals")


class SupportTicket(Base):
    """Support tickets from salons to superadmin"""
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    priority = Column(String, default="normal")  # low, normal, high, urgent
    category = Column(String, nullable=True)  # billing, technical, feature_request, other
    admin_response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="support_tickets")
    creator = relationship("User", foreign_keys=[created_by], backref="created_tickets")
    responder = relationship("User", foreign_keys=[responded_by], backref="responded_tickets")


class CustomerComplaint(Base):
    """Complaints/issues from customers to salons"""
    __tablename__ = "customer_complaints"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String, nullable=False)  # Store name even if customer deleted
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    priority = Column(String, default="normal")  # low, normal, high, urgent
    category = Column(String, nullable=True)  # service, product, appointment, other
    salon_response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="customer_complaints")
    customer = relationship("Customer", backref="complaints")
    responder = relationship("User", foreign_keys=[responded_by], backref="responded_complaints")


class Review(Base):
    """Customer reviews and ratings for salons"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String, nullable=False)  # Store name even if customer deleted
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)  # Optional review text
    is_approved = Column(Integer, default=1)  # 1 for approved, 0 for pending moderation
    is_visible = Column(Integer, default=1)  # 1 for visible, 0 for hidden by salon
    salon_response = Column(Text, nullable=True)  # Salon's response to the review
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="reviews")
    customer = relationship("Customer", backref="reviews")


class SpecialRequest(Base):
    """Special request booking - customer describes what they want, salon reviews and quotes"""
    __tablename__ = "special_requests"

    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)  # Optional service category
    
    # Customer info
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    
    # Request details
    description = Column(Text, nullable=False)  # What the customer wants
    is_offsite = Column(Integer, default=0)  # 1 for off-site, 0 for on-site
    offsite_location = Column(Text, nullable=True)  # Customer's location for off-site service
    preferred_date = Column(DateTime, nullable=True)  # Optional preferred date
    
    # Images - stored as comma-separated file IDs
    image_file_ids = Column(Text, nullable=True)  # Comma-separated cloud_file IDs
    
    # Status workflow
    status = Column(String, default="pending")  # pending, quoted, accepted, rejected, cancelled, completed
    
    # Salon's quote/response
    quoted_amount = Column(Integer, nullable=True)  # Quoted price in cents
    quoted_products = Column(Text, nullable=True)  # JSON array of suggested product IDs and names
    salon_notes = Column(Text, nullable=True)  # Salon's notes/response to the request
    quoted_at = Column(DateTime, nullable=True)  # When salon provided quote
    
    # Customer response to quote
    customer_response = Column(Text, nullable=True)  # Customer's response to quote
    responded_at = Column(DateTime, nullable=True)  # When customer responded
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    salon = relationship("Salon", backref="special_requests")
    customer = relationship("Customer", backref="special_requests")
    service = relationship("Service", backref="special_requests")

