from __future__ import annotations
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# Salon schemas
class SalonBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class SalonCreate(SalonBase):
    pass


class SalonRegistration(BaseModel):
    """Multi-step salon registration"""
    # Step 1: Salon info
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: EmailStr
    
    # Step 2: Admin user
    admin_full_name: str
    admin_email: EmailStr
    admin_password: str
    
    # Step 3: Selected services (IDs from service templates)
    selected_service_template_ids: List[int]
    
    # Step 4: Plan selection
    plan_id: int
    billing_cycle: Optional[str] = "monthly"  # "monthly" or "yearly"
    auto_debit: Optional[int] = 0  # 0 for manual, 1 for auto-debit


class SalonResponse(SalonBase):
    id: int
    slug: str
    plan_id: Optional[int] = None
    billing_cycle: str
    auto_debit: int
    opening_hour: int
    closing_hour: int
    max_concurrent_slots: int
    logo_type: str
    logo_icon_name: str
    logo_file_id: Optional[int] = None
    layout_pattern: str
    client_theme_name: str
    custom_css: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    default_completion_message: Optional[str] = None
    default_cancellation_message: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    facebook_url: Optional[str] = None
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class SalonHoursUpdate(BaseModel):
    """Update salon operating hours"""
    opening_hour: int
    closing_hour: int
    max_concurrent_slots: Optional[int] = None

    class Config:
        from_attributes = True


class SalonUpdate(BaseModel):
    """Update salon settings"""
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    opening_hour: Optional[int] = None
    closing_hour: Optional[int] = None
    max_concurrent_slots: Optional[int] = None
    billing_cycle: Optional[str] = None
    auto_debit: Optional[int] = None
    layout_pattern: Optional[str] = None
    client_theme_name: Optional[str] = None
    custom_css: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    default_completion_message: Optional[str] = None
    default_cancellation_message: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    facebook_url: Optional[str] = None

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    salon_id: Optional[int] = None
    is_superadmin: Optional[int] = 0


class UserResponse(UserBase):
    id: int
    salon_id: Optional[int] = None
    is_admin: int
    is_superadmin: int
    created_at: datetime

    class Config:
        from_attributes = True


# Customer schemas
class CustomerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Service schemas
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    duration_minutes: Optional[int] = None


class ServiceCreate(ServiceBase):
    service_template_id: Optional[int] = None  # NULL for custom services
    is_custom: Optional[int] = 0  # 1 for custom, 0 for template-based


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    duration_minutes: Optional[int] = None


class ServiceResponse(ServiceBase):
    id: int
    salon_id: int
    service_template_id: Optional[int] = None
    is_custom: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# SubService schemas
class SubServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    pricing_type: Optional[str] = "hourly"  # "hourly" or "one_time"
    booking_type: Optional[str] = "both"  # "timed", "full_day", or "both"
    hourly_rate: int  # Price per hour in cents (or total price for one_time)
    min_hours: Optional[int] = 1  # Minimum hours required


class SubServiceCreate(SubServiceBase):
    service_id: int


class SubServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pricing_type: Optional[str] = None
    booking_type: Optional[str] = None
    hourly_rate: Optional[int] = None
    min_hours: Optional[int] = None
    is_active: Optional[int] = None


class SubServiceResponse(SubServiceBase):
    id: int
    service_id: int
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# SubService Product schemas
class SubServiceProductResponse(BaseModel):
    id: int
    sub_service_id: int
    product_id: int
    created_at: datetime
    product: Optional['ProductResponse'] = None  # Include product details

    class Config:
        from_attributes = True


class SubServiceWithProducts(SubServiceResponse):
    """SubService response including suggested products"""
    suggested_products: List[SubServiceProductResponse] = []

    class Config:
        from_attributes = True


class ServiceWithSubServices(ServiceResponse):
    """Service response including its sub-services"""
    sub_services: List[SubServiceResponse] = []

    class Config:
        from_attributes = True


# Appointment schemas
class AppointmentBase(BaseModel):
    customer_id: int
    service_id: int
    appointment_date: datetime
    notes: Optional[str] = None


class AppointmentCreate(BaseModel):
    salon_id: Optional[int] = None  # Required for platform-wide customers, optional if customer has salon_id
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    service_id: int
    sub_service_id: Optional[int] = None  # Optional sub-service selection
    hours: Optional[float] = 1.0  # Number of hours for sub-service billing
    appointment_date: datetime
    notes: Optional[str] = None
    # Off-site booking fields
    is_offsite: Optional[bool] = False
    offsite_location: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    salon_id: int
    customer_id: int
    service_id: int
    sub_service_id: Optional[int] = None
    hours: float
    appointment_date: datetime
    slot_number: int
    status: str
    status_message: Optional[str] = None
    notes: Optional[str] = None
    # Off-site booking fields
    is_offsite: int = 0
    offsite_location: Optional[str] = None
    offsite_extra_charge: Optional[int] = None
    offsite_response: Optional[str] = None
    offsite_status: Optional[str] = None
    offsite_responded_at: Optional[datetime] = None
    created_at: datetime
    customer: CustomerResponse
    service: ServiceResponse
    sub_service: Optional[SubServiceResponse] = None

    class Config:
        from_attributes = True


class OffsiteQuoteRequest(BaseModel):
    """Request to quote an off-site appointment"""
    extra_charge: int  # Extra charge in cents
    response: Optional[str] = None  # Optional note to customer


class OffsiteRejectRequest(BaseModel):
    """Request to reject an off-site appointment"""
    response: str  # Reason for rejection


class AppointmentStatusUpdate(BaseModel):
    """Request to complete or cancel an appointment with a message"""
    message: str  # Message to customer about the status change


class AvailabilityCheck(BaseModel):
    """Request to check slot availability"""
    service_id: int
    appointment_date: datetime


class AvailabilityResponse(BaseModel):
    """Response with slot availability"""
    is_available: bool
    slot_number: Optional[int] = None
    error_message: Optional[str] = None


class AppointmentListResponse(BaseModel):
    """Paginated list of appointments"""
    appointments: List[AppointmentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None
    salon_id: Optional[int] = None
    is_superadmin: Optional[int] = 0


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Plan schemas
class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[int] = 0  # Deprecated: in cents
    monthly_price: int = 0  # Monthly price in cents
    yearly_price: int = 0  # Yearly price in cents
    discount_percentage: Optional[float] = 0  # Discount percentage
    features: Optional[str] = None
    max_services: Optional[int] = 5  # Maximum services
    max_staff: Optional[int] = 1  # Maximum staff members
    max_appointments_per_month: Optional[int] = 0  # 0 for unlimited
    max_customers: Optional[int] = 0  # 0 for unlimited
    max_concurrent_slots: Optional[int] = 1  # Maximum concurrent time slots
    has_analytics: Optional[int] = 0
    has_advanced_reporting: Optional[int] = 0
    has_custom_branding: Optional[int] = 0
    has_priority_support: Optional[int] = 0


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None  # Deprecated
    monthly_price: Optional[int] = None
    yearly_price: Optional[int] = None
    discount_percentage: Optional[float] = None
    features: Optional[str] = None
    max_services: Optional[int] = None
    max_staff: Optional[int] = None
    max_appointments_per_month: Optional[int] = None
    max_customers: Optional[int] = None
    max_concurrent_slots: Optional[int] = None
    has_analytics: Optional[int] = None
    has_advanced_reporting: Optional[int] = None
    has_custom_branding: Optional[int] = None
    has_priority_support: Optional[int] = None
    is_active: Optional[int] = None


class PlanResponse(PlanBase):
    id: int
    is_active: int
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Service Template schemas
class ServiceTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class ServiceTemplateCreate(ServiceTemplateBase):
    pass


class ServiceTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[int] = None


class ServiceTemplateResponse(ServiceTemplateBase):
    id: int
    is_active: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Cloud File schemas
class CloudFileBase(BaseModel):
    filename: str
    file_path: str
    file_type: str
    file_size: Optional[int] = None


class CloudFileResponse(CloudFileBase):
    id: int
    uploaded_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LogoUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[int] = None
    file_url: Optional[str] = None


class LogoIconUpdate(BaseModel):
    logo_icon_name: str


# CloudFile schemas
class CloudFileBase(BaseModel):
    filename: str
    file_type: str


class CloudFileCreate(CloudFileBase):
    file_path: str
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None


class CloudFileResponse(CloudFileBase):
    id: int
    file_path: str
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LogoUploadResponse(BaseModel):
    """Response after logo upload"""
    success: bool
    message: str
    file_id: Optional[int] = None
    file_url: Optional[str] = None


class LogoIconUpdate(BaseModel):
    """Update salon logo to use predefined icon"""
    logo_icon_name: str


class LogoUrlUpdate(BaseModel):
    """Update salon logo with URL or media ID"""
    logo_url: Optional[str] = None  # Legacy support
    filename: Optional[str] = None
    file_size: Optional[int] = None
    media_id: Optional[int] = None  # New preferred method


class FileUrlUpload(BaseModel):
    """File URL upload from frontend (customer special requests)"""
    file_url: str
    filename: str
    file_type: str
    file_size: Optional[int] = None


class ProductImageUrlUpload(BaseModel):
    """Product image URL upload from frontend"""
    image_url: str
    filename: Optional[str] = None
    file_size: Optional[int] = None


class ProductImageUrlsUpload(BaseModel):
    """Multiple product image URLs or media IDs upload from frontend"""
    image_urls: Optional[List[str]] = None  # Legacy support
    filenames: Optional[List[str]] = None
    media_ids: Optional[List[int]] = None  # New preferred method


# Product Category schemas
class ProductCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProductCategoryCreate(ProductCategoryBase):
    salon_id: Optional[int] = None  # Optional - superadmin can specify salon


class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProductCategoryResponse(ProductCategoryBase):
    id: int
    salon_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Product schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: int  # Price in cents
    discount_percentage: float = 0  # Discount percentage (0-100)
    quantity: int = 0
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    salon_id: Optional[int] = None  # Optional - superadmin can specify salon
    media_ids: Optional[List[int]] = None  # Optional list of MediaUpload IDs for images


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    discount_percentage: Optional[float] = None
    quantity: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[int] = None


class ProductResponse(ProductBase):
    id: int
    salon_id: int
    image_file_id: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None  # Category name
    is_active: int
    created_at: datetime
    updated_at: datetime
    images: List["ProductImageResponse"] = []

    class Config:
        from_attributes = True


# Product Image schemas
class ProductImageResponse(BaseModel):
    id: int
    product_id: int
    file_id: Optional[int] = None
    image_url: Optional[str] = None
    display_order: int
    is_primary: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductImageUpdate(BaseModel):
    display_order: Optional[int] = None
    is_primary: Optional[int] = None


# Cart schemas
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductResponse

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    customer_id: int
    salon_id: int
    items: List[CartItemResponse]
    
    @property
    def total_amount(self) -> int:
        return sum(item.product.price * item.quantity for item in self.items)

    class Config:
        from_attributes = True


# Order schemas
class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_purchase: int
    product: ProductResponse

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    salon_id: int
    customer_id: int
    order_number: str
    total_amount: int
    status: str
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True


class PaymentInitiate(BaseModel):
    payment_method: str  # "paystack" or "flutterwave"
    callback_url: str


# Customer Authentication schemas

# Platform-wide registration (new - no salon_id required)
class PlatformCustomerRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str


# Legacy salon-specific registration (kept for backward compatibility)
class CustomerRegister(BaseModel):
    salon_id: Optional[int] = None  # Made optional - will be deprecated
    name: str
    email: EmailStr
    phone: str
    password: str


class CustomerLogin(BaseModel):
    email: EmailStr
    password: str


class CustomerToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CustomerAuthResponse(BaseModel):
    id: int
    salon_id: Optional[int] = None  # Made optional for platform-wide customers
    name: str
    email: str
    phone: Optional[str] = None
    is_verified: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerTokenWithInfo(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer: CustomerAuthResponse


# SalonCustomer schemas
class SalonCustomerBase(BaseModel):
    source: str = "appointment"  # "appointment", "purchase", "manual"
    notes: Optional[str] = None
    loyalty_points: Optional[int] = 0
    is_favorite: Optional[int] = 0


class SalonCustomerCreate(SalonCustomerBase):
    salon_id: int
    customer_id: int


class SalonCustomerResponse(SalonCustomerBase):
    id: int
    salon_id: int
    customer_id: int
    total_spent: int
    total_appointments: int
    first_interaction_at: datetime
    last_interaction_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SalonCustomerWithCustomer(SalonCustomerResponse):
    """SalonCustomer with embedded customer details for salon dashboard"""
    customer: CustomerAuthResponse


class CustomerWithSalonRelationships(CustomerAuthResponse):
    """Customer with their salon relationships"""
    salon_customers: Optional[List[SalonCustomerResponse]] = []


# Wallet schemas
class WalletResponse(BaseModel):
    id: int
    salon_id: int
    balance: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    id: int
    wallet_id: int
    order_id: Optional[int] = None
    amount: int
    type: str
    status: str
    payment_reference: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletWithSalon(WalletResponse):
    salon_name: Optional[str] = None
    salon_slug: Optional[str] = None


class WalletTransactionWithDetails(WalletTransactionResponse):
    salon_id: Optional[int] = None
    salon_name: Optional[str] = None
    order_number: Optional[str] = None


# Bank Account schemas
class BankAccountCreate(BaseModel):
    account_name: str
    account_number: str
    bank_name: str
    bank_code: Optional[str] = None
    is_default: Optional[int] = 0


class BankAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    is_default: Optional[int] = None


class BankAccountResponse(BaseModel):
    id: int
    salon_id: int
    account_name: str
    account_number: str
    bank_name: str
    bank_code: Optional[str] = None
    is_default: int
    is_verified: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Withdrawal schemas
class WithdrawalCreate(BaseModel):
    bank_account_id: int
    amount: int
    notes: Optional[str] = None


class WithdrawalResponse(BaseModel):
    id: int
    wallet_id: int
    bank_account_id: int
    amount: int
    status: str
    reference: str
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    transaction_reference: Optional[str] = None
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WithdrawalWithDetails(WithdrawalResponse):
    salon_id: Optional[int] = None
    salon_name: Optional[str] = None
    bank_account: Optional[BankAccountResponse] = None
    processor_name: Optional[str] = None


class WithdrawalUpdate(BaseModel):
    status: str  # approved, rejected, completed, failed
    admin_notes: Optional[str] = None
    transaction_reference: Optional[str] = None


# Support Ticket schemas (Salon to Superadmin)
class SupportTicketBase(BaseModel):
    subject: str
    message: str
    category: Optional[str] = None  # billing, technical, feature_request, other
    priority: Optional[str] = "normal"  # low, normal, high, urgent


class SupportTicketCreate(SupportTicketBase):
    pass


class SupportTicketUpdate(BaseModel):
    status: Optional[str] = None  # open, in_progress, resolved, closed
    priority: Optional[str] = None
    admin_response: Optional[str] = None


class SupportTicketResponse(SupportTicketBase):
    id: int
    salon_id: int
    created_by: Optional[int] = None
    status: str
    admin_response: Optional[str] = None
    responded_by: Optional[int] = None
    responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    salon_name: Optional[str] = None  # For superadmin view
    creator_name: Optional[str] = None  # Who created the ticket

    class Config:
        from_attributes = True


# Customer Complaint schemas (Customer to Salon)
class CustomerComplaintBase(BaseModel):
    subject: str
    message: str
    category: Optional[str] = None  # service, product, appointment, other
    priority: Optional[str] = "normal"  # low, normal, high, urgent


class CustomerComplaintCreate(CustomerComplaintBase):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    salon_id: int  # Required for public submission


class CustomerComplaintUpdate(BaseModel):
    status: Optional[str] = None  # open, in_progress, resolved, closed
    priority: Optional[str] = None
    salon_response: Optional[str] = None


class CustomerComplaintResponse(CustomerComplaintBase):
    id: int
    salon_id: int
    customer_id: Optional[int] = None
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    status: str
    salon_response: Optional[str] = None
    responded_by: Optional[int] = None
    responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    responder_name: Optional[str] = None  # Who responded

    class Config:
        from_attributes = True


# Review schemas (Customer reviews for Salons)
class ReviewBase(BaseModel):
    rating: int  # 1-5 stars
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    salon_id: int


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None


class ReviewResponse(ReviewBase):
    id: int
    salon_id: int
    customer_id: Optional[int] = None
    customer_name: str
    is_approved: int
    is_visible: int
    salon_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewSalonResponse(BaseModel):
    """For salon owner to respond to a review"""
    salon_response: str


class SalonRatingSummary(BaseModel):
    """Summary of salon ratings"""
    average_rating: float
    total_reviews: int
    rating_distribution: dict  # e.g., {"5": 10, "4": 5, "3": 2, "2": 1, "1": 0}


# ===================== Special Request Schemas =====================

class SpecialRequestCreate(BaseModel):
    """Create a new special request"""
    salon_id: Optional[int] = None  # Required for platform-wide customers
    customer_name: str
    customer_email: EmailStr
    customer_phone: Optional[str] = None
    service_id: Optional[int] = None
    description: str
    is_offsite: Optional[int] = 0
    offsite_location: Optional[str] = None
    preferred_date: Optional[datetime] = None
    image_file_ids: Optional[str] = None  # Legacy: Comma-separated file IDs
    media_ids: Optional[List[int]] = None  # New preferred method


class SpecialRequestQuote(BaseModel):
    """Salon provides a quote for the special request"""
    quoted_amount: int  # Price in cents
    quoted_products: Optional[str] = None  # JSON array of product suggestions
    salon_notes: Optional[str] = None


class SpecialRequestReject(BaseModel):
    """Salon rejects the special request"""
    salon_notes: str  # Reason for rejection


class SpecialRequestResponse(BaseModel):
    """Response schema for special requests"""
    id: int
    salon_id: int
    customer_id: int
    service_id: Optional[int] = None
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    description: str
    is_offsite: int
    offsite_location: Optional[str] = None
    preferred_date: Optional[datetime] = None
    image_file_ids: Optional[str] = None
    status: str
    quoted_amount: Optional[int] = None
    quoted_products: Optional[str] = None
    salon_notes: Optional[str] = None
    quoted_at: Optional[datetime] = None
    customer_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested objects
    service: Optional[ServiceResponse] = None

    class Config:
        from_attributes = True


# ==================== NOTIFICATION SCHEMAS ====================

class PushSubscriptionCreate(BaseModel):
    """Create a new push subscription"""
    endpoint: str
    p256dh_key: str
    auth_key: str
    device_name: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    """Response for push subscription"""
    id: int
    recipient_type: str
    recipient_id: int
    endpoint: str
    device_name: Optional[str] = None
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Response schema for notifications"""
    id: int
    notification_type: str
    title: str
    message: str
    recipient_type: str
    recipient_id: int
    salon_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    channels_sent: Optional[str] = None
    is_read: int
    read_at: Optional[datetime] = None
    extra_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    total_pages: int


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preferences"""
    notification_type: Optional[str] = "all"
    email_enabled: Optional[int] = 1
    sms_enabled: Optional[int] = 1
    push_enabled: Optional[int] = 1


class NotificationPreferenceResponse(BaseModel):
    """Response for notification preferences"""
    id: int
    recipient_type: str
    recipient_id: int
    notification_type: str
    email_enabled: int
    sms_enabled: int
    push_enabled: int

    class Config:
        from_attributes = True


class MarkNotificationsRead(BaseModel):
    """Mark notifications as read"""
    notification_ids: List[int]


class VapidPublicKeyResponse(BaseModel):
    """Response containing VAPID public key for client"""
    public_key: str


# Media Upload schemas
class MediaUploadResponse(BaseModel):
    """Response for media upload status"""
    id: int
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    gcs_path: Optional[str] = None
    public_url: Optional[str] = None
    bucket_name: Optional[str] = None
    folder: str
    salon_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MediaUploadListResponse(BaseModel):
    """Response for list of media uploads"""
    uploads: List[MediaUploadResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class MediaUploadBatchResponse(BaseModel):
    """Response for batch upload"""
    uploads: List[MediaUploadResponse]
    total_files: int
    message: str


# Rebuild models to resolve forward references
SubServiceProductResponse.model_rebuild()
