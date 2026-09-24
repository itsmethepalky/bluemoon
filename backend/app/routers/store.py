from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user


router = APIRouter(prefix="/api/store", tags=["Store"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product_to_out(product: models.Product) -> schemas.StoreProductOut:
    images = sorted(
        product.images or [],
        key=lambda image: (
            not image.is_primary,
            image.sort_order,
            image.id,
        ),
    )

    return schemas.StoreProductOut(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        brand_id=product.brand_id,
        unit_price=Decimal(str(product.unit_price)),
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        images=[
            schemas.StoreProductImageOut(
                id=image.id,
                image_url=image.image_url,
                is_primary=image.is_primary,
                sort_order=image.sort_order,
            )
            for image in images
        ],
    )


def _order_to_out(order: models.Order) -> schemas.StoreOrderOut:
    items = []

    for item in order.items:
        items.append(
            schemas.StoreOrderItemOut(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
                subtotal=item.subtotal,
                product_name=item.product.name if item.product else None,
            )
        )

    return schemas.StoreOrderOut(
        id=order.id,
        order_no=order.order_no,
        status=order.status,
        subtotal=order.subtotal,
        discount=order.discount,
        tax=order.tax,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        shipping_address=order.shipping_address,
        phone=order.phone,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
    )


def _get_customer(
    db: Session,
    user: models.Profile,
) -> models.Customer:
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.user_id == user.id)
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer profile not found.",
        )

    return customer


# ---------------------------------------------------------------------------
# Store catalog
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=List[schemas.StoreCategoryOut])
def list_store_categories(
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Category)
        .filter(models.Category.is_active.is_(True))
        .order_by(models.Category.name.asc())
        .all()
    )


@router.get("/brands", response_model=List[schemas.StoreBrandOut])
def list_store_brands(
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Brand)
        .filter(models.Brand.is_active.is_(True))
        .order_by(models.Brand.name.asc())
        .all()
    )


@router.get("/products", response_model=List[schemas.StoreProductOut])
def list_store_products(
    search: Optional[str] = Query(default=None, max_length=100),
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    in_stock: bool = False,
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.Product)
        .options(joinedload(models.Product.images))
        .filter(models.Product.is_active.is_(True))
    )

    if search:
        search_text = search.strip()

        if search_text:
            pattern = f"%{search_text}%"
            query = query.filter(
                models.Product.name.ilike(pattern)
                | models.Product.sku.ilike(pattern)
            )

    if category_id is not None:
        query = query.filter(
            models.Product.category_id == category_id
        )

    if brand_id is not None:
        query = query.filter(
            models.Product.brand_id == brand_id
        )

    if in_stock:
        query = query.filter(
            models.Product.stock_quantity > 0
        )

    products = (
        query
        .order_by(models.Product.name.asc())
        .all()
    )

    return [_product_to_out(product) for product in products]


@router.get(
    "/products/{product_id}",
    response_model=schemas.StoreProductOut,
)
def get_store_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(models.Product)
        .options(joinedload(models.Product.images))
        .filter(
            models.Product.id == product_id,
            models.Product.is_active.is_(True),
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return _product_to_out(product)


# ---------------------------------------------------------------------------
# Customer orders
# ---------------------------------------------------------------------------

@router.get(
    "/orders",
    response_model=List[schemas.StoreOrderOut],
)
def list_my_orders(
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    if user.role != models.UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account required.",
        )

    customer = _get_customer(db, user)

    orders = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.items)
            .joinedload(models.OrderItem.product)
        )
        .filter(models.Order.customer_id == customer.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )

    return [_order_to_out(order) for order in orders]


@router.get(
    "/orders/{order_id}",
    response_model=schemas.StoreOrderOut,
)
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    if user.role != models.UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account required.",
        )

    customer = _get_customer(db, user)

    order = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.items)
            .joinedload(models.OrderItem.product)
        )
        .filter(
            models.Order.id == order_id,
            models.Order.customer_id == customer.id,
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    return _order_to_out(order)


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@router.post(
    "/orders",
    response_model=schemas.StoreOrderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_store_order(
    payload: schemas.StoreOrderCreate,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    if user.role != models.UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account required.",
        )

    customer = _get_customer(db, user)

    # Combine duplicate product IDs so the same product cannot be inserted
    # into the order multiple times accidentally.
    quantities = {}

    for line in payload.items:
        quantities[line.product_id] = (
            quantities.get(line.product_id, 0) + line.quantity
        )

    try:
        subtotal = Decimal("0.00")
        locked_products = {}

        # Lock every product row until this transaction commits.
        for product_id, quantity in quantities.items():
            product = (
                db.query(models.Product)
                .filter(
                    models.Product.id == product_id,
                    models.Product.is_active.is_(True),
                )
                .with_for_update()
                .first()
            )

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {product_id} not found.",
                )

            if product.stock_quantity < quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient stock for '{product.name}'. "
                        f"Available: {product.stock_quantity}, "
                        f"requested: {quantity}."
                    ),
                )

            locked_products[product_id] = product
            subtotal += (
                Decimal(str(product.unit_price)) * Decimal(quantity)
            )

        discount = Decimal("0.00")
        tax = Decimal("0.00")
        total = subtotal - discount + tax

        order = models.Order(
            order_no="PENDING",
            customer_id=customer.id,
            status=models.OrderStatus.pending,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total_amount=total,
            payment_method=payload.payment_method,
            payment_status=models.PaymentStatus.unpaid,
            shipping_address=payload.shipping_address.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            notes=payload.notes.strip() if payload.notes else None,
        )

        db.add(order)
        db.flush()

        order.order_no = f"ORD-{order.id:06d}"

        for product_id, quantity in quantities.items():
            product = locked_products[product_id]

            unit_price = Decimal(str(product.unit_price))
            line_subtotal = unit_price * Decimal(quantity)

            db.add(
                models.OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount=Decimal("0.00"),
                    subtotal=line_subtotal,
                )
            )

            product.stock_quantity -= quantity

        db.commit()

        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create order.",
        )

    # Reload relationships after commit.
    order = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.items)
            .joinedload(models.OrderItem.product)
        )
        .filter(models.Order.id == order.id)
        .first()
    )

    return _order_to_out(order)
