from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


def _to_out(product: models.Product) -> schemas.ProductOut:
    return schemas.ProductOut.model_validate(product)


@router.get(
    "",
    response_model=List[schemas.ProductOut],
)
def list_products(
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    products = (
        db.query(models.Product)
        .order_by(models.Product.name)
        .all()
    )

    return [_to_out(product) for product in products]


@router.get(
    "/low-stock",
    response_model=List[schemas.ProductOut],
)
def low_stock_products(
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    products = (
        db.query(models.Product)
        .filter(
            models.Product.stock_quantity
            <= models.Product.reorder_level
        )
        .order_by(models.Product.stock_quantity)
        .all()
    )

    return [_to_out(product) for product in products]


@router.get(
    "/{product_id}",
    response_model=schemas.ProductOut,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return _to_out(product)


@router.post(
    "",
    response_model=schemas.ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    data = payload.model_dump()

    if "sku" in data and data["sku"]:
        data["sku"] = data["sku"].strip()

    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()

    if "description" in data and data["description"]:
        data["description"] = data["description"].strip()

    if data.get("sku"):
        existing = (
            db.query(models.Product)
            .filter(models.Product.sku == data["sku"])
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="SKU already exists",
            )

    if data.get("image_url"):
        image_url = data["image_url"].strip()
        lowered = image_url.lower()

        if lowered.startswith(
            ("javascript:", "data:", "vbscript:")
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid image URL",
            )

        data["image_url"] = image_url

    product = models.Product(**data)

    db.add(product)

    try:
        db.commit()
        db.refresh(product)

    except Exception as exc:
        db.rollback()

        message = str(exc).lower()

        if (
            "unique" in message
            or "duplicate" in message
            or "sku" in message
        ):
            raise HTTPException(
                status_code=400,
                detail="SKU already exists",
            )

        raise HTTPException(
            status_code=400,
            detail="Could not create product",
        )

    return _to_out(product)


@router.put(
    "/{product_id}",
    response_model=schemas.ProductOut,
)
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    data = payload.model_dump(
        exclude_unset=True
    )

    if "sku" in data and data["sku"] is not None:
        data["sku"] = data["sku"].strip()

        if data["sku"] != product.sku:
            existing = (
                db.query(models.Product)
                .filter(
                    models.Product.sku == data["sku"],
                    models.Product.id != product_id,
                )
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="SKU already exists",
                )

    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()

    if (
        "description" in data
        and data["description"] is not None
    ):
        data["description"] = data["description"].strip()

    if "image_url" in data:
        if data["image_url"] is not None:
            image_url = data["image_url"].strip()
            lowered = image_url.lower()

            if lowered.startswith(
                (
                    "javascript:",
                    "data:",
                    "vbscript:",
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid image URL",
                )

            data["image_url"] = image_url

    # Stock is intentionally not accepted here.
    # Inventory changes must go through adjust_stock()
    # so they are protected by a row lock.
    data.pop("stock_quantity", None)

    for field, value in data.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Could not update product",
        )

    return _to_out(product)


@router.post(
    "/{product_id}/adjust-stock",
    response_model=schemas.ProductOut,
)
def adjust_stock(
    product_id: int,
    payload: schemas.StockAdjust,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    """
    Manual stock correction.

    The product row is locked with FOR UPDATE before
    reading and changing stock. This prevents concurrent
    stock adjustments from overwriting each other.
    """

    if product_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID",
        )

    if payload.delta == 0:
        raise HTTPException(
            status_code=400,
            detail="Stock adjustment cannot be zero",
        )

    try:
        # Lock the product row until this transaction
        # commits or rolls back.
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
                detail="Product not found",
            )

        if (
            product.stock_quantity is None
            or product.stock_quantity < 0
        ):
            db.rollback()

            raise HTTPException(
                status_code=409,
                detail="Product stock data is invalid",
            )

        new_qty = (
            product.stock_quantity
            + payload.delta
        )

        if new_qty < 0:
            db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Stock quantity cannot go below zero",
            )

        product.stock_quantity = new_qty

        db.commit()
        db.refresh(product)

        return _to_out(product)

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Could not adjust product stock",
        )
