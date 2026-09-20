from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff, require_admin

router = APIRouter(prefix="/api/products", tags=["Products & Inventory"])


def _to_out(product: models.Product) -> schemas.ProductOut:
    out = schemas.ProductOut.model_validate(product)
    out.category_name = product.category.name if product.category else None
    out.brand_name = product.brand.name if product.brand else None
    return out


@router.get("", response_model=List[schemas.ProductOut])
def list_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    query = db.query(models.Product)
    if active_only:
        query = query.filter(models.Product.is_active.is_(True))
    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Product.name.ilike(like), models.Product.sku.ilike(like)))
    products = query.order_by(models.Product.name).all()
    return [_to_out(p) for p in products]


@router.get("/low-stock", response_model=List[schemas.ProductOut])
def low_stock_products(db: Session = Depends(get_db), _user=Depends(require_staff)):
    products = (
        db.query(models.Product)
        .filter(models.Product.is_active.is_(True))
        .filter(models.Product.stock_quantity <= models.Product.reorder_level)
        .order_by(models.Product.stock_quantity)
        .all()
    )
    return [_to_out(p) for p in products]


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), _user=Depends(require_staff)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_out(product)


@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: schemas.ProductCreate, db: Session = Depends(get_db), _user=Depends(require_staff)
):
    if db.query(models.Product).filter(models.Product.sku == payload.sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_out(product)


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump(exclude_unset=True)
    if "sku" in data and data["sku"] != product.sku:
        if db.query(models.Product).filter(models.Product.sku == data["sku"]).first():
            raise HTTPException(status_code=400, detail="SKU already exists")
    for field, value in data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return _to_out(product)


@router.post("/{product_id}/adjust-stock", response_model=schemas.ProductOut)
def adjust_stock(
    product_id: int,
    payload: schemas.StockAdjust,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    """Manual stock correction (e.g. stock count, damage, spoilage)."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    new_qty = product.stock_quantity + payload.delta
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock quantity cannot go below zero")
    product.stock_quantity = new_qty
    db.commit()
    db.refresh(product)
    return _to_out(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Soft delete: important sales/purchase history stays intact."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    return None
