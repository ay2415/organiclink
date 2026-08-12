import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Date, Text, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True) # farmer, consumer, retailer, restaurant, institution, manufacturer, admin
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    town = Column(String(100), nullable=True)
    county = Column(String(100), nullable=True)
    eircode = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocode_source = Column(String(32), nullable=True) # eircode_routing_key, town_centroid, fallback
    status = Column(String(50), default="verified", index=True) # pending, verified, suspended
    buyer_type = Column(String(50), nullable=True) # Consumer, Retailer, Restaurant, Institution, Aggregator, Supermarket, CSA
    business_name = Column(String(255), nullable=True)
    vat_number = Column(String(100), nullable=True)
    delivery_address = Column(Text, nullable=True)
    typical_order_size = Column(String(100), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="owner", uselist=False, cascade="all, delete-orphan")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    farm_name = Column(String(255), nullable=False)
    town = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    eircode = Column(String(20), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    size_hectares = Column(Float, nullable=True)
    years_farming_organic = Column(Float, default=0.0)
    provides_own_transport = Column(Boolean, default=True)
    produce_list = Column(JSON, default=list) # e.g. ["onion", "milk", "apple"]
    photo_urls = Column(JSON, default=list) # up to 5 farm photos
    organic_cert_body = Column(String(100), nullable=True) # e.g. IOA, Organic Trust, Demeter, Other
    organic_cert_number = Column(String(100), nullable=True)
    cert_issue_date = Column(Date, nullable=True)
    cert_expiry_date = Column(Date, nullable=True)
    cert_doc_url = Column(String(500), nullable=True)
    verification_status = Column(String(50), default="verified", index=True) # pending_verification, verified, expired
    farm_type = Column(String(50), default="mixed") # dairy, produce, mixed
    description = Column(Text, nullable=True)
    reputation_score = Column(Float, default=0.0)
    total_orders_completed = Column(Integer, default=0)
    average_quality_score = Column(Float, nullable=True)
    verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    owner = relationship("User", back_populates="farm")
    production_history = relationship("ProductionHistory", back_populates="farm", cascade="all, delete-orphan")
    production_logs = relationship("ProductionLog", back_populates="farm", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="farm", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="farm", cascade="all, delete-orphan")
    delivery_rules = relationship("DeliveryRule", back_populates="farm", uselist=False, cascade="all, delete-orphan")
    delivery_slots = relationship("DeliverySlot", back_populates="farm", cascade="all, delete-orphan")


class ProductionHistory(Base):
    __tablename__ = "production_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    product_type = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True) # null = annual total
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False) # kg, litre
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="production_history")


class ProductType(Base):
    __tablename__ = "product_types"

    id = Column(String(100), primary_key=True) # e.g. "milk", "onion", "tomato"
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False) # dairy, vegetables, fruit
    default_unit = Column(String(20), default="kg") # kg, litre
    default_log_type = Column(String(20), default="batch") # daily, batch
    cv_gradable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class ProductionLog(Base):
    __tablename__ = "production_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    product_type = Column(String(100), nullable=False, index=True)
    log_type = Column(String(20), nullable=False, default="batch") # daily, batch
    log_date = Column(Date, nullable=False, index=True)
    batch_reference = Column(String(100), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False) # kg, litre
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="production_logs")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_path = Column(String(500), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String(50), nullable=False) # listing, farm_inspection, delivery_inspection, certificate_doc, profile
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_name = Column(String(255), nullable=False)
    hub_name = Column(String(255), nullable=False) # The processor/manufacturer
    product_type = Column(String(100), nullable=False, index=True)
    committed_quantity = Column(Float, nullable=False)
    quantity_unit = Column(String(20), nullable=False) # kg, litre
    period = Column(String(20), default="month") # day, week, month
    price_per_unit = Column(Float, nullable=False)
    collection_schedule = Column(String(255), nullable=True)
    quality_requirements = Column(Text, nullable=True)
    hub_lat = Column(Float, nullable=True)
    hub_lng = Column(Float, nullable=True)
    status = Column(String(50), default="active", index=True) # active, on_hold, expired
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="contracts")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    product_type = Column(String(100), nullable=False, index=True)
    variety = Column(String(100), nullable=True)
    production_date = Column(Date, nullable=False)
    quantity_total = Column(Float, nullable=False, default=0.0)
    quantity_reserved = Column(Float, default=0.0)
    quantity_sold = Column(Float, default=0.0)
    available_quantity = Column(Float, nullable=False)
    quantity_unit = Column(String(20), nullable=False) # kg, litre, box
    price_per_unit = Column(Float, nullable=False)
    buyer_types_open_to = Column(JSON, default=list) # e.g. ["consumer", "retailer", "restaurant"]
    provides_transport = Column(Boolean, default=False)
    cv_grading_supported = Column(Boolean, default=False)
    is_bulk = Column(Boolean, default=False)
    bulk_summary = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    quality_grade = Column(String(5), nullable=True) # A, B, C, R
    quality_score = Column(Float, nullable=True)
    quality_inspection_id = Column(String(36), ForeignKey("quality_inspections.id", ondelete="SET NULL"), nullable=True)
    demand_score = Column(Float, nullable=True)
    demand_is_estimate = Column(Boolean, default=True)
    status = Column(String(50), default="pending_quality", index=True) # pending_quality, listed, sold_out, expired
    description = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    farm = relationship("Farm", back_populates="products")
    inspection = relationship("QualityInspection", foreign_keys=[quality_inspection_id])


class DeliveryRule(Base):
    __tablename__ = "delivery_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farmer_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    delivers = Column(Boolean, default=True)
    max_radius_km = Column(Integer, default=30)
    min_order_value_eur = Column(Float, default=0.0)
    min_order_qty = Column(Float, default=0.0)
    delivery_fee_eur = Column(Float, default=0.0)
    free_over_eur = Column(Float, nullable=True)
    offers_pickup = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="delivery_rules")


class DeliverySlot(Base):
    __tablename__ = "delivery_slots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farmer_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10), nullable=False) # e.g. "09:00"
    end_time = Column(String(10), nullable=False)   # e.g. "13:00"
    slot_type = Column(String(20), default="delivery") # delivery, pickup
    pickup_location = Column(Text, nullable=True)
    pickup_lat = Column(Float, nullable=True)
    pickup_lng = Column(Float, nullable=True)
    capacity_kg = Column(Float, default=100.0)
    booked_kg = Column(Float, default=0.0)
    zone_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    farm = relationship("Farm", back_populates="delivery_slots")


class DeliveryRun(Base):
    __tablename__ = "delivery_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farmer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = Column(String(36), ForeignKey("delivery_slots.id", ondelete="CASCADE"), nullable=True, index=True)
    zone_name = Column(String(100), nullable=False) # e.g. "Limerick City Run"
    zone_routing_key = Column(String(10), nullable=False, index=True) # e.g. "V94"
    target_kg = Column(Float, default=50.0)
    committed_kg = Column(Float, default=0.0)
    status = Column(String(20), default="open", index=True) # open, confirmed, cancelled, delivered
    closes_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now)


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    inspection_level = Column(String(50), nullable=False) # farm, delivery
    image_url = Column(String(500), nullable=False)
    cv_results = Column(JSON, nullable=True)
    quality_score = Column(Float, nullable=False)
    quality_grade = Column(String(5), nullable=False)
    defects_detected = Column(JSON, default=list)
    model_confidence = Column(Float, nullable=True)
    model_version = Column(String(50), default="effnetb0-v1")
    inspector_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    farmer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    quantity_unit = Column(String(20), nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    delivery_date = Column(Date, nullable=False)
    delivery_address = Column(Text, nullable=False)
    transport_by = Column(String(20), default="farmer") # farmer, buyer
    delivery_type = Column(String(30), default="direct") # direct, collection_point
    collection_point_name = Column(String(200), nullable=True)
    special_requests = Column(Text, nullable=True)
    status = Column(String(50), default="pending", index=True)
    # Statuses: pending, accepted, rejected, negotiating, quality_verified, in_transit, delivered, disputed, paid, completed
    negotiation_history = Column(JSON, default=list)
    farm_inspection_id = Column(String(36), ForeignKey("quality_inspections.id", ondelete="SET NULL"), nullable=True)
    delivery_inspection_id = Column(String(36), ForeignKey("quality_inspections.id", ondelete="SET NULL"), nullable=True)
    quality_variance_percent = Column(Float, nullable=True)
    variance_acceptable = Column(Boolean, nullable=True)
    dispute_flag = Column(Boolean, default=False)
    dispute_reason = Column(Text, nullable=True)
    dispute_status = Column(String(50), nullable=True) # open, resolved
    dispute_resolution = Column(String(50), nullable=True) # full_payment, partial_payment, refund_buyer
    dispute_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    product = relationship("Product")
    farmer = relationship("User", foreign_keys=[farmer_id])
    buyer = relationship("User", foreign_keys=[buyer_id])
    farm_inspection = relationship("QualityInspection", foreign_keys=[farm_inspection_id])
    delivery_inspection = relationship("QualityInspection", foreign_keys=[delivery_inspection_id])


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    farmer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    buyer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    payment_method = Column(String(50), default="platform_mock") # bank_transfer, platform_mock
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    status = Column(String(50), default="pending", index=True) # pending, held, paid, partial, refunded
    invoice_url = Column(String(500), nullable=True)
    reference_number = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    order = relationship("Order")


class RatingReview(Base):
    __tablename__ = "ratings_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    rater_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ratee_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating_stars = Column(Integer, nullable=False) # 1-5
    quality_consistency = Column(Integer, default=5) # 1-5
    timeliness = Column(Integer, default=5) # 1-5
    communication = Column(Integer, default=5) # 1-5
    reliability = Column(Integer, default=5) # 1-5
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    hub_directory_id = Column(String(36), ForeignKey("hubs_directory.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    message_text = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    actor_id = Column(String(36), nullable=True)
    actor_role = Column(String(50), nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)


class HubDirectory(Base):
    __tablename__ = "hubs_directory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    hub_type = Column(String(50), nullable=False) # manufacturer, store, processor, restaurant
    town = Column(String(100), nullable=False)
    county = Column(String(100), nullable=False)
    eircode = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accepts_products = Column(JSON, default=list) # e.g. ["onion", "milk", "apple"]
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
