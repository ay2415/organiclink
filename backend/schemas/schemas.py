from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str # farmer, consumer, retailer, restaurant, institution, manufacturer, admin
    name: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str


# --- Profile Schemas ---
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    town: Optional[str] = None
    county: Optional[str] = None
    eircode: Optional[str] = None
    buyer_type: Optional[str] = None
    business_name: Optional[str] = None
    vat_number: Optional[str] = None
    delivery_address: Optional[str] = None
    typical_order_size: Optional[str] = None
    # Farmer extra fields
    farm_name: Optional[str] = None
    size_hectares: Optional[float] = None
    years_farming_organic: Optional[float] = None
    organic_cert_body: Optional[str] = None
    organic_cert_number: Optional[str] = None
    cert_expiry_date: Optional[date] = None
    produce_list: Optional[List[str]] = None
    provides_own_transport: Optional[bool] = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    role: str
    status: str
    town: Optional[str] = None
    county: Optional[str] = None
    eircode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_source: Optional[str] = None
    buyer_type: Optional[str] = None
    business_name: Optional[str] = None
    vat_number: Optional[str] = None
    delivery_address: Optional[str] = None
    typical_order_size: Optional[str] = None
    profile_photo_url: Optional[str] = None
    created_at: datetime
    farm: Optional[Dict[str, Any]] = None


class PublicProfileResponse(BaseModel):
    id: str
    name: str
    role: str
    status: str
    town: Optional[str] = None
    county: Optional[str] = None
    profile_photo_url: Optional[str] = None
    verified: bool = True
    reputation_score: float = 90.0
    total_completed_orders: int = 0
    average_quality_score: Optional[float] = None
    member_since: datetime
    farm: Optional[Dict[str, Any]] = None
    recent_reviews: List[Dict[str, Any]] = []
    active_listings: List[Dict[str, Any]] = []


class FarmResponse(BaseModel):
    id: str
    user_id: str
    farm_name: str
    town: str
    county: str
    eircode: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_hectares: Optional[float] = None
    years_farming_organic: Optional[float] = 0.0
    provides_own_transport: Optional[bool] = True
    produce_list: List[str] = []
    photo_urls: List[str] = []
    organic_cert_body: Optional[str] = None
    organic_cert_number: Optional[str] = None
    cert_issue_date: Optional[date] = None
    cert_expiry_date: Optional[date] = None
    cert_doc_url: Optional[str] = None
    farm_type: Optional[str] = "mixed"
    description: Optional[str] = None
    reputation_score: float = 100.0
    total_orders_completed: int = 0
    average_quality_score: Optional[float] = None
    verified: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    phone: Optional[str] = None
    town: Optional[str] = None
    county: Optional[str] = None
    eircode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_source: Optional[str] = None
    status: Optional[str] = "verified"
    buyer_type: Optional[str] = None
    business_name: Optional[str] = None
    vat_number: Optional[str] = None
    delivery_address: Optional[str] = None
    typical_order_size: Optional[str] = None
    profile_photo_url: Optional[str] = None
    verified: bool = True
    is_active: bool = True
    created_at: datetime
    farm: Optional[FarmResponse] = None

    class Config:
        from_attributes = True


# --- Farm & Production Schemas ---
class FarmCreate(BaseModel):
    farm_name: str
    town: str
    county: str
    eircode: str
    size_hectares: Optional[float] = 10.0
    produce_list: List[str] = []
    organic_cert_body: Optional[str] = "Irish Organic Association"
    organic_cert_number: Optional[str] = None
    cert_issue_date: Optional[date] = None
    cert_expiry_date: Optional[date] = None
    farm_type: str = "mixed" # dairy, produce, mixed
    description: Optional[str] = None


class FarmUpdate(BaseModel):
    farm_name: Optional[str] = None
    town: Optional[str] = None
    county: Optional[str] = None
    eircode: Optional[str] = None
    size_hectares: Optional[float] = None
    produce_list: Optional[List[str]] = None
    description: Optional[str] = None



    class Config:
        from_attributes = True


class ProductionCreate(BaseModel):
    product_type: str
    year: int
    month: Optional[int] = None
    quantity: float
    unit: str # kg, litre


class ProductionResponse(BaseModel):
    id: str
    farm_id: str
    product_type: str
    year: int
    month: Optional[int] = None
    quantity: float
    unit: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Contract Schemas ---
class ContractCreate(BaseModel):
    contract_name: str
    hub_name: str
    product_type: str
    committed_quantity: float
    quantity_unit: str # kg, litre
    period: str = "month" # day, week, month
    price_per_unit: float
    collection_schedule: Optional[str] = None
    status: str = "active"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ContractUpdate(BaseModel):
    contract_name: Optional[str] = None
    committed_quantity: Optional[float] = None
    price_per_unit: Optional[float] = None
    status: Optional[str] = None


class ContractResponse(BaseModel):
    id: str
    farm_id: str
    contract_name: str
    hub_name: str
    product_type: str
    committed_quantity: float
    quantity_unit: str
    period: str
    price_per_unit: float
    collection_schedule: Optional[str] = None
    quality_requirements: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days_remaining: Optional[int] = None
    fulfillment_percent: Optional[float] = 100.0
    created_at: datetime

    class Config:
        from_attributes = True


# --- Product & Marketplace Schemas ---
class ProductResponse(BaseModel):
    id: str
    farm_id: str
    farm_name: Optional[str] = None
    farmer_name: Optional[str] = None
    town: Optional[str] = None
    county: Optional[str] = None
    distance_km: Optional[float] = None
    farmer_reputation: Optional[float] = None
    product_type: str
    variety: Optional[str] = None
    production_date: date
    available_quantity: float
    quantity_unit: str
    price_per_unit: float
    buyer_types_open_to: List[str] = []
    provides_transport: bool
    cv_grading_supported: bool = False
    quantity_total: Optional[float] = None
    quantity_reserved: Optional[float] = None
    quantity_sold: Optional[float] = None
    image_url: Optional[str] = None
    quality_grade: Optional[str] = None
    quality_score: Optional[float] = None
    quality_inspection_id: Optional[str] = None
    cv_breakdown: Optional[Dict[str, Any]] = None
    demand_score: Optional[float] = None
    demand_is_estimate: bool = True
    status: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SurplusSuggestion(BaseModel):
    product_type: str
    produced_quantity: float
    committed_quantity: float
    suggested_surplus: float
    unit: str


# --- Quality Inspection Schemas ---
class QualityInspectionResponse(BaseModel):
    id: str
    product_id: Optional[str] = None
    order_id: Optional[str] = None
    inspection_level: str # farm, delivery
    image_url: str
    cv_results: Optional[Dict[str, Any]] = None
    quality_score: float
    quality_grade: str
    defects_detected: List[str] = []
    model_confidence: Optional[float] = None
    model_version: str
    inspector_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Order Schemas ---
class OrderCreate(BaseModel):
    product_id: str
    quantity: float
    delivery_date: date
    delivery_address: str
    transport_by: str = "farmer" # farmer, buyer
    delivery_type: str = "direct" # direct, collection_point
    collection_point_name: Optional[str] = None
    special_requests: Optional[str] = None


class OrderNegotiate(BaseModel):
    quantity: Optional[float] = None
    price_per_unit: Optional[float] = None
    delivery_date: Optional[date] = None
    message: Optional[str] = None


class OrderReject(BaseModel):
    reason: str


class OrderDisputeResolve(BaseModel):
    resolution: str # full_payment, partial_payment, refund_buyer
    rationale: str
    partial_percent: Optional[float] = 50.0


class OrderNegotiateProposal(BaseModel):
    proposed_price_per_unit: float
    note: Optional[str] = None


class OrderNegotiateResponse(BaseModel):
    action: str # accept, reject
    note: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    product_id: str
    farmer_id: str
    buyer_id: str
    product_type: Optional[str] = None
    farmer_name: Optional[str] = None
    buyer_name: Optional[str] = None
    farm_name: Optional[str] = None
    quantity: float
    quantity_unit: str
    price_per_unit: float
    total_price: float
    delivery_date: date
    delivery_address: str
    transport_by: str
    delivery_type: Optional[str] = "direct"
    collection_point_name: Optional[str] = None
    special_requests: Optional[str] = None
    status: str
    negotiation_history: List[Dict[str, Any]] = []
    farm_inspection: Optional[QualityInspectionResponse] = None
    delivery_inspection: Optional[QualityInspectionResponse] = None
    quality_variance_percent: Optional[float] = None
    variance_acceptable: Optional[bool] = None
    dispute_flag: bool = False
    dispute_reason: Optional[str] = None
    dispute_status: Optional[str] = None
    dispute_resolution: Optional[str] = None
    dispute_rationale: Optional[str] = None
    invoice_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Payment & Rating Schemas ---
class PaymentResponse(BaseModel):
    id: str
    order_id: str
    farmer_id: str
    buyer_id: str
    amount: float
    currency: str
    payment_method: str
    due_date: date
    paid_date: Optional[date] = None
    status: str
    invoice_url: Optional[str] = None
    reference_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentMarkPaid(BaseModel):
    reference_number: str
    payment_method: str = "bank_transfer"


class RatingCreate(BaseModel):
    order_id: str
    ratee_id: str
    rating_stars: int # 1-5
    quality_consistency: int = 5
    timeliness: int = 5
    communication: int = 5
    reliability: int = 5
    review_text: Optional[str] = None


class RatingResponse(BaseModel):
    id: str
    order_id: str
    rater_id: str
    ratee_id: str
    rating_stars: int
    review_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Message & Notification Schemas ---
class MessageCreate(BaseModel):
    recipient_id: Optional[str] = None
    hub_directory_id: Optional[str] = None
    order_id: Optional[str] = None
    product_id: Optional[str] = None
    message_text: str


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_name: Optional[str] = None
    hub_directory_id: Optional[str] = None
    hub_name: Optional[str] = None
    order_id: Optional[str] = None
    product_id: Optional[str] = None
    message_text: str
    attachment_url: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    notification_type: str
    message: str
    action_url: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Hub Directory Schema ---
class HubDirectoryResponse(BaseModel):
    id: str
    name: str
    hub_type: str
    town: str
    county: str
    eircode: str
    latitude: float
    longitude: float
    distance_km: Optional[float] = None
    accepts_products: List[str] = []
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    class Config:
        from_attributes = True


# --- Admin Schemas ---
class AdminFarmVerify(BaseModel):
    verified: bool
    note: Optional[str] = None


class AdminSettingsUpdate(BaseModel):
    variance_tolerance_percent: Optional[float] = 10.0
    min_listing_grade: Optional[str] = "C"
    commission_percent: Optional[float] = 5.0
    payment_terms_days: Optional[int] = 14
