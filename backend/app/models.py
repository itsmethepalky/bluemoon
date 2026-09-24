import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text, Numeric
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .database import Base


# ---------------------------------------------------------------------------
# Enums (values match the Postgres enum types created in the Supabase
# migrations - see database/migrations/ for the source of truth)
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    customer = "customer"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    card = "card"
    mobile = "mobile"
    credit = "credit"
    cod = "cod"


class PaymentStatus(str, enum.Enum):
    paid = "paid"
    partial = "partial"
    unpaid = "unpaid"


class SaleStatus(str, enum.Enum):
    completed = "completed"
    returned = "returned"
    partially_returned = "partially_returned"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    ready = "ready"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    returned = "returned"


# ---------------------------------------------------------------------------
# Profiles & customers
# ---------------------------------------------------------------------------
# NOTE: there is no local "users" table anymore. Login identities live in
# Supabase Auth (the managed `auth.users` table). `Profile` is a 1:1 side
# table (id = auth.users.id) holding the app-specific role/full name/etc.
# A Postgres trigger (private.handle_new_auth_user) creates the Profile
# row automatically whenever someone signs up through Supabase Auth.

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    role = Column(Enum(UserRole, name="user_role"), default=UserRole.customer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer_profile = relationship(
        "Customer", back_populates="user", uselist=False
    )


class Customer(Base):
    """A shop customer. May optionally have a linked Supabase-authenticated profile."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("profiles.id"), unique=True, nullable=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    address = Column(String(255), nullable=True)
    credit_limit = Column(Float, default=0.0, nullable=False)
    credit_balance = Column(Float, default=0.0, nullable=False)  # what the customer currently owes
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("Profile", back_populates="customer_profile")
    sales = relationship("Sale", back_populates="customer")
    orders = relationship("Order", back_populates="customer")


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(60), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    cost_price = Column(Float, nullable=False, default=0.0)
    unit_price = Column(Float, nullable=False, default=0.0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# E-commerce
# ---------------------------------------------------------------------------

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path = Column(Text, nullable=False)
    image_url = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="images")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(30), unique=True, nullable=False)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
    )

    status = Column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.pending,
        nullable=False,
    )

    subtotal = Column(Numeric(12, 2), default=0, nullable=False)
    discount = Column(Numeric(12, 2), default=0, nullable=False)
    tax = Column(Numeric(12, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), default=0, nullable=False)

    payment_method = Column(
        Enum(PaymentMethod, name="payment_method"),
        default=PaymentMethod.cash,
        nullable=False,
    )

    payment_status = Column(
        Enum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.unpaid,
        nullable=False,
    )

    shipping_address = Column(Text, nullable=False)
    phone = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    customer = relationship("Customer", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=True,
    )

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), default=0, nullable=False)
    discount = Column(Numeric(12, 2), default=0, nullable=False)
    subtotal = Column(Numeric(12, 2), default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


# ---------------------------------------------------------------------------
# Suppliers & purchases
# ---------------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    purchases = relationship("Purchase", back_populates="supplier")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(30), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    recorded_by = Column(PGUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, default=0.0, nullable=False)
    notes = Column(String(255), nullable=True)

    supplier = relationship("Supplier", back_populates="purchases")
    recorder = relationship("Profile")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")


# ---------------------------------------------------------------------------
# Sales / POS
# ---------------------------------------------------------------------------

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)  # null = walk-in
    cashier_id = Column(PGUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    sale_date = Column(DateTime, default=datetime.utcnow)
    subtotal = Column(Float, default=0.0, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    amount_paid = Column(Float, default=0.0, nullable=False)
    payment_method = Column(Enum(PaymentMethod, name="payment_method"), default=PaymentMethod.cash, nullable=False)
    payment_status = Column(Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.unpaid, nullable=False)
    status = Column(Enum(SaleStatus, name="sale_status"), default=SaleStatus.completed, nullable=False)

    customer = relationship("Customer", back_populates="sales")
    cashier = relationship("Profile")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    returns = relationship("Return", back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    subtotal = Column(Float, nullable=False)
    returned_quantity = Column(Integer, default=0, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    sale_item_id = Column(Integer, ForeignKey("sale_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    refund_amount = Column(Float, default=0.0, nullable=False)
    processed_by = Column(PGUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    return_date = Column(DateTime, default=datetime.utcnow)

    sale = relationship("Sale", back_populates="returns")
    sale_item = relationship("SaleItem")
    processor = relationship("Profile")
