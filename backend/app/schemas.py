from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import UserRole, PaymentMethod, PaymentStatus, SaleStatus


# ---------------------------------------------------------------------------
# Auth / Profiles
# ---------------------------------------------------------------------------
# NOTE: sign-up/sign-in happen via Supabase Auth on the frontend (there is
# no local password or token issuance any more), so there is no `Token`
# schema here. `ProfileOut` is what GET /api/auth/me and the staff-accounts
# endpoints return; `UserCreate`/`UserUpdate` are used by admins to manage
# staff/admin logins, which under the hood calls the Supabase Admin Auth API.

class ProfileBase(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.staff


class UserCreate(ProfileBase):
    """Admin creates a staff/admin login. Requires an email (used to sign in)."""
    email: EmailStr
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6)


class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Catalog: categories, brands, products
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BrandBase(BaseModel):
    name: str


class BrandCreate(BrandBase):
    pass


class BrandOut(BrandBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProductBase(BaseModel):
    sku: str
    name: str
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    cost_price: float = 0.0
    unit_price: float = 0.0
    stock_quantity: int = 0
    reorder_level: int = 5
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    cost_price: Optional[float] = None
    unit_price: Optional[float] = None
    reorder_level: Optional[int] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StockAdjust(BaseModel):
    delta: int  # positive to add stock, negative to remove
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Suppliers & purchases
# ---------------------------------------------------------------------------

class SupplierBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PurchaseItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)


class PurchaseCreate(BaseModel):
    supplier_id: int
    notes: Optional[str] = None
    items: List[PurchaseItemIn]


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_cost: float
    subtotal: float


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_no: str
    supplier_id: int
    supplier_name: Optional[str] = None
    recorded_by: Optional[UUID] = None
    purchase_date: datetime
    total_amount: float
    notes: Optional[str] = None
    items: List[PurchaseItemOut] = []


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: float = 0.0


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[float] = None


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    credit_balance: float
    created_at: datetime


class CreditPayment(BaseModel):
    amount: float = Field(gt=0)
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Sales / POS
# ---------------------------------------------------------------------------

class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    discount: float = Field(default=0.0, ge=0)


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItemIn]
    discount: float = Field(default=0.0, ge=0)  # overall order discount
    tax: float = Field(default=0.0, ge=0)
    payment_method: PaymentMethod = PaymentMethod.cash
    amount_paid: float = Field(default=0.0, ge=0)


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: float
    discount: float
    subtotal: float
    returned_quantity: int


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_no: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    cashier_id: Optional[UUID] = None
    cashier_name: Optional[str] = None
    sale_date: datetime
    subtotal: float
    discount: float
    tax: float
    total_amount: float
    amount_paid: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: SaleStatus
    items: List[SaleItemOut] = []


class ReturnCreate(BaseModel):
    sale_item_id: int
    quantity: int = Field(gt=0)
    reason: Optional[str] = None


class ReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    sale_item_id: int
    quantity: int
    reason: Optional[str] = None
    refund_amount: float
    processed_by: Optional[UUID] = None
    return_date: datetime


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    today_sales_total: float
    today_sales_count: int
    month_sales_total: float
    low_stock_count: int
    total_products: int
    total_customers: int
    outstanding_credit: float


class SalesPoint(BaseModel):
    label: str
    total: float


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    quantity_sold: int
    revenue: float


class InventoryStatusItem(BaseModel):
    category: str
    stock_value: float
    quantity: int
