from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff, get_current_user

router = APIRouter(prefix="/api/sales", tags=["Sales / POS"])


def _to_out(sale: models.Sale) -> schemas.SaleOut:
    out = schemas.SaleOut.model_validate(sale)
    out.customer_name = sale.customer.name if sale.customer else "Walk-in customer"
    out.cashier_name = sale.cashier.full_name if sale.cashier else None
    for item_out, item in zip(out.items, sale.items):
        item_out.product_name = item.product.name if item.product else None
    return out


@router.get("", response_model=List[schemas.SaleOut])
def list_sales(
    start: Optional[date] = None,
    end: Optional[date] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    query = db.query(models.Sale).options(
        joinedload(models.Sale.items).joinedload(models.SaleItem.product),
        joinedload(models.Sale.customer),
        joinedload(models.Sale.cashier),
    )

    if user.role == models.UserRole.customer:
        # Customers may only ever see their own purchase history
        own_customer = db.query(models.Customer).filter(models.Customer.user_id == user.id).first()
        query = query.filter(models.Sale.customer_id == (own_customer.id if own_customer else -1))
    elif customer_id:
        query = query.filter(models.Sale.customer_id == customer_id)

    if start:
        query = query.filter(models.Sale.sale_date >= datetime.combine(start, datetime.min.time()))
    if end:
        query = query.filter(models.Sale.sale_date <= datetime.combine(end, datetime.max.time()))

    sales = query.order_by(models.Sale.sale_date.desc()).all()
    return [_to_out(s) for s in sales]


@router.get("/{sale_id}", response_model=schemas.SaleOut)
def get_sale(
    sale_id: int, db: Session = Depends(get_db), user: models.Profile = Depends(get_current_user)
):
    sale = db.query(models.Sale).filter(models.Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    if user.role == models.UserRole.customer:
        own_customer = db.query(models.Customer).filter(models.Customer.user_id == user.id).first()
        if not own_customer or sale.customer_id != own_customer.id:
            raise HTTPException(status_code=404, detail="Sale not found")
    return _to_out(sale)


@router.post("", response_model=schemas.SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: schemas.SaleCreate,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(require_staff),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="A sale needs at least one item")

    customer = None
    if payload.customer_id:
        customer = db.query(models.Customer).filter(models.Customer.id == payload.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

    if payload.payment_method == models.PaymentMethod.credit and not customer:
        raise HTTPException(status_code=400, detail="A customer is required for credit sales")

    sale = models.Sale(
        invoice_no="PENDING",
        customer_id=customer.id if customer else None,
        cashier_id=user.id,
        sale_date=datetime.utcnow(),
        discount=payload.discount,
        tax=payload.tax,
        payment_method=payload.payment_method,
    )
    db.add(sale)
    db.flush()  # assign sale.id

    subtotal = 0.0
    for line in payload.items:
        product = db.query(models.Product).filter(models.Product.id == line.product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
        if product.stock_quantity < line.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for '{product.name}' (have {product.stock_quantity}, "
                f"requested {line.quantity})",
            )

        line_subtotal = round((product.unit_price * line.quantity) - line.discount, 2)
        subtotal += line_subtotal

        db.add(
            models.SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=line.quantity,
                unit_price=product.unit_price,
                discount=line.discount,
                subtotal=line_subtotal,
            )
        )
        product.stock_quantity -= line.quantity

    total_amount = round(subtotal - payload.discount + payload.tax, 2)
    amount_paid = payload.amount_paid

    if payload.payment_method == models.PaymentMethod.credit and amount_paid == 0:
        # Fully on credit
        payment_status = models.PaymentStatus.unpaid
    elif amount_paid >= total_amount:
        payment_status = models.PaymentStatus.paid
        amount_paid = total_amount
    elif amount_paid > 0:
        payment_status = models.PaymentStatus.partial
    else:
        payment_status = models.PaymentStatus.unpaid

    outstanding = round(total_amount - amount_paid, 2)
    if outstanding > 0:
        if not customer:
            db.rollback()
            raise HTTPException(
                status_code=400, detail="A customer is required to leave a balance on credit"
            )
        customer.credit_balance += outstanding

    sale.subtotal = round(subtotal, 2)
    sale.total_amount = total_amount
    sale.amount_paid = amount_paid
    sale.payment_status = payment_status
    sale.invoice_no = f"INV-{sale.id:06d}"

    db.commit()
    db.refresh(sale)
    return _to_out(sale)
