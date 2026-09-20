from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff

router = APIRouter(prefix="/api/purchases", tags=["Purchases"])


def _to_out(purchase: models.Purchase) -> schemas.PurchaseOut:
    out = schemas.PurchaseOut.model_validate(purchase)
    out.supplier_name = purchase.supplier.name if purchase.supplier else None
    for item_out, item in zip(out.items, purchase.items):
        item_out.product_name = item.product.name if item.product else None
    return out


@router.get("", response_model=List[schemas.PurchaseOut])
def list_purchases(
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    query = db.query(models.Purchase).options(
        joinedload(models.Purchase.items).joinedload(models.PurchaseItem.product),
        joinedload(models.Purchase.supplier),
    )
    if supplier_id:
        query = query.filter(models.Purchase.supplier_id == supplier_id)
    purchases = query.order_by(models.Purchase.purchase_date.desc()).all()
    return [_to_out(p) for p in purchases]


@router.get("/{purchase_id}", response_model=schemas.PurchaseOut)
def get_purchase(purchase_id: int, db: Session = Depends(get_db), _user=Depends(require_staff)):
    purchase = db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return _to_out(purchase)


@router.post("", response_model=schemas.PurchaseOut, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: schemas.PurchaseCreate,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(require_staff),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="A purchase needs at least one item")

    supplier = db.query(models.Supplier).filter(models.Supplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    purchase = models.Purchase(
        reference_no="PENDING",
        supplier_id=payload.supplier_id,
        recorded_by=user.id,
        notes=payload.notes,
        purchase_date=datetime.utcnow(),
        total_amount=0.0,
    )
    db.add(purchase)
    db.flush()  # get purchase.id without committing

    total = 0.0
    for item in payload.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        subtotal = round(item.quantity * item.unit_cost, 2)
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
        # Purchasing stock automatically increases inventory
        product.stock_quantity += item.quantity
        # Keep the product's cost price current for profit reporting
        product.cost_price = item.unit_cost

    purchase.total_amount = round(total, 2)
    purchase.reference_no = f"PO-{purchase.id:06d}"

    db.commit()
    db.refresh(purchase)
    return _to_out(purchase)
