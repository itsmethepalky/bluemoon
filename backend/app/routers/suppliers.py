from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff, require_admin

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


@router.get("", response_model=List[schemas.SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _user=Depends(require_staff)):
    return db.query(models.Supplier).order_by(models.Supplier.name).all()


@router.post("", response_model=schemas.SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: schemas.SupplierCreate, db: Session = Depends(get_db), _user=Depends(require_staff)
):
    supplier = models.Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(
    supplier_id: int,
    payload: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for field, value in payload.model_dump().items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)
):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.purchases:
        raise HTTPException(
            status_code=400, detail="Cannot delete a supplier with recorded purchases"
        )
    db.delete(supplier)
    db.commit()
    return None
