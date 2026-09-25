from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff


router = APIRouter(
    prefix="/api/purchases",
    tags=["Purchases"],
)


def _to_out(purchase: models.Purchase) -> schemas.PurchaseOut:
    out = schemas.PurchaseOut.model_validate(purchase)

    for item_out, item in zip(out.items, purchase.items):
        item_out.product_name = (
            item.product.name
            if item.product
            else None
        )

    return out


@router.get(
    "",
    response_model=List[schemas.PurchaseOut],
)
def list_purchases(
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    purchases = (
        db.query(models.Purchase)
        .options(
            joinedload(models.Purchase.items)
            .joinedload(models.PurchaseItem.product)
        )
        .order_by(models.Purchase.purchase_date.desc())
        .all()
    )

    return [_to_out(purchase) for purchase in purchases]


@router.get(
    "/{purchase_id}",
    response_model=schemas.PurchaseOut,
)
def get_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    purchase = (
        db.query(models.Purchase)
        .options(
            joinedload(models.Purchase.items)
            .joinedload(models.PurchaseItem.product)
        )
        .filter(
            models.Purchase.id == purchase_id
        )
        .first()
    )

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found",
        )

    return _to_out(purchase)


@router.post(
    "",
    response_model=schemas.PurchaseOut,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase(
    payload: schemas.PurchaseCreate,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    if not payload.items:
        raise HTTPException(
            status_code=400,
            detail="A purchase needs at least one item",
        )

    # Prevent the same product from appearing multiple times.
    quantities = {}

    for item in payload.items:
        if item.product_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid product ID",
            )

        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Purchase quantity must be greater than zero",
            )

        if item.product_id in quantities:
            raise HTTPException(
                status_code=400,
                detail=(
                    "A product cannot appear more than once "
                    "in the same purchase"
                ),
            )

        quantities[item.product_id] = item.quantity

    purchase = models.Purchase(
        supplier_id=payload.supplier_id,
        invoice_no=payload.invoice_no,
        purchase_date=datetime.utcnow(),
        total_amount=0.0,
        created_by=user.id,
    )

    db.add(purchase)
    db.flush()

    locked_products = {}

    try:
        # Lock every affected product in a consistent order.
        # The lock remains active until commit/rollback.
        for product_id in sorted(quantities):
            product = (
                db.query(models.Product)
                .filter(
                    models.Product.id == product_id
                )
                .with_for_update()
                .first()
            )

            if not product:
                db.rollback()

                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Product {product_id} "
                        "not found"
                    ),
                )

            if (
                product.stock_quantity is None
                or product.stock_quantity < 0
            ):
                db.rollback()

                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Product '{product.name}' "
                        "has invalid stock data"
                    ),
                )

            locked_products[product_id] = product

        total = 0.0

        # Use the locked product objects while creating
        # purchase items and increasing stock.
        for item in payload.items:
            product = locked_products[item.product_id]

            subtotal = round(
                item.quantity * item.unit_cost,
                2,
            )

            if subtotal < 0:
                db.rollback()

                raise HTTPException(
                    status_code=400,
                    detail="Purchase item total cannot be negative",
                )

            total += subtotal

            db.add(
                models.PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    subtotal=subtotal,
                )
            )

            # Product row is already locked.
            product.stock_quantity += item.quantity
            product.cost_price = item.unit_cost

        purchase.total_amount = round(
            total,
            2,
        )

        purchase.reference_no = (
            f"PO-{purchase.id:06d}"
        )

        db.commit()
        db.refresh(purchase)

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Could not create purchase",
        )

    # Reload relationships after commit so _to_out() has
    # the same complete response behavior as before.
    purchase = (
        db.query(models.Purchase)
        .options(
            joinedload(models.Purchase.items)
            .joinedload(models.PurchaseItem.product)
        )
        .filter(
            models.Purchase.id == purchase.id
        )
        .first()
    )

    if not purchase:
        raise HTTPException(
            status_code=500,
            detail="Purchase was created but could not be loaded",
        )

    return _to_out(purchase)
