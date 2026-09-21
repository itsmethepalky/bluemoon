from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff, require_admin

router = APIRouter(prefix="/api/brands", tags=["Brands"])


@router.get("", response_model=List[schemas.BrandOut])
def list_brands(
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    return db.query(models.Brand).order_by(models.Brand.name).all()


@router.post(
    "",
    response_model=schemas.BrandOut,
    status_code=status.HTTP_201_CREATED,
)
def create_brand(
    payload: schemas.BrandCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Brand name is required",
        )

    if db.query(models.Brand).filter(
        models.Brand.name.ilike(name)
    ).first():
        raise HTTPException(
            status_code=400,
            detail="Brand already exists",
        )

    brand = models.Brand(name=name)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    return brand


@router.put(
    "/{brand_id}",
    response_model=schemas.BrandOut,
)
def update_brand(
    brand_id: int,
    payload: schemas.BrandCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    brand = (
        db.query(models.Brand)
        .filter(models.Brand.id == brand_id)
        .first()
    )

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found",
        )

    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Brand name is required",
        )

    duplicate = (
        db.query(models.Brand)
        .filter(
            models.Brand.name.ilike(name),
            models.Brand.id != brand_id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=400,
            detail="Brand already exists",
        )

    brand.name = name

    db.commit()
    db.refresh(brand)

    return brand


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    brand = (
        db.query(models.Brand)
        .filter(models.Brand.id == brand_id)
        .first()
    )

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found",
        )

    if brand.products:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a brand that still has products",
        )

    db.delete(brand)
    db.commit()

    return None
