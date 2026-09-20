from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff

router = APIRouter(prefix="/api/returns", tags=["Returns"])


@router.get("", response_model=List[schemas.ReturnOut])
def list_returns(db: Session = Depends(get_db), _user=Depends(require_staff)):
    return db.query(models.Return).order_by(models.Return.return_date.desc()).all()


@router.post("", response_model=schemas.ReturnOut, status_code=status.HTTP_201_CREATED)
def create_return(
    payload: schemas.ReturnCreate,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(require_staff),
):
    sale_item = (
        db.query(models.SaleItem)
        .filter(models.SaleItem.id == payload.sale_item_id)
        .first()
    )

    if not sale_item:
        raise HTTPException(status_code=404, detail="Sale item not found")

    remaining = sale_item.quantity - sale_item.returned_quantity

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Return quantity must be greater than zero")

    if payload.quantity > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Only {remaining} unit(s) from this sale item can still be returned",
        )

    sale = (
        db.query(models.Sale)
        .filter(models.Sale.id == sale_item.sale_id)
        .first()
    )

    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # The line subtotal already includes the line-level discount.
    unit_value = (
        sale_item.subtotal / sale_item.quantity
        if sale_item.quantity
        else 0
    )
    refund_amount = round(unit_value * payload.quantity, 2)

    return_row = models.Return(
        sale_id=sale_item.sale_id,
        sale_item_id=sale_item.id,
        quantity=payload.quantity,
        reason=payload.reason,
        refund_amount=refund_amount,
        processed_by=user.id,
        return_date=datetime.utcnow(),
    )
    db.add(return_row)

    # Put the returned stock back into inventory.
    product = (
        db.query(models.Product)
        .filter(models.Product.id == sale_item.product_id)
        .first()
    )

    if product:
        product.stock_quantity += payload.quantity

    sale_item.returned_quantity += payload.quantity

    # Keep the customer's outstanding credit synchronized with the
    # reduced invoice total.
    old_total = round(sale.total_amount, 2)
    old_paid = round(sale.amount_paid, 2)
    old_outstanding = max(0.0, round(old_total - old_paid, 2))

    # Reduce the financial value of the sale by the returned amount.
    sale.total_amount = max(
        0.0,
        round(old_total - refund_amount, 2),
    )

    new_outstanding = max(
        0.0,
        round(sale.total_amount - sale.amount_paid, 2),
    )

    credit_reduction = round(
        old_outstanding - new_outstanding,
        2,
    )

    if (
        credit_reduction > 0
        and sale.payment_method == models.PaymentMethod.credit
        and sale.customer
    ):
        sale.customer.credit_balance = max(
            0.0,
            round(
                sale.customer.credit_balance - credit_reduction,
                2,
            ),
        )

    # If the returned amount exceeds the unpaid portion, the remaining
    # refund comes from the amount that had already been paid.
    if sale.amount_paid > sale.total_amount:
        sale.amount_paid = round(sale.total_amount, 2)

    # Recalculate payment status against the new net invoice total.
    if sale.total_amount <= 0:
        sale.amount_paid = 0.0
        sale.payment_status = models.PaymentStatus.paid
    elif sale.amount_paid >= sale.total_amount:
        sale.amount_paid = round(sale.total_amount, 2)
        sale.payment_status = models.PaymentStatus.paid
    elif sale.amount_paid > 0:
        sale.payment_status = models.PaymentStatus.partial
    else:
        sale.payment_status = models.PaymentStatus.unpaid

    all_returned = all(
        item.returned_quantity >= item.quantity
        for item in sale.items
    )

    any_returned = any(
        item.returned_quantity > 0
        for item in sale.items
    )

    if all_returned:
        sale.status = models.SaleStatus.returned
    elif any_returned:
        sale.status = models.SaleStatus.partially_returned

    db.commit()
    db.refresh(return_row)

    return return_row
