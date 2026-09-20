from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff, require_admin, get_current_user

router = APIRouter(prefix="/api/customers", tags=["Customers"])


def _visible_to(user: models.Profile, customer: models.Customer) -> bool:
    if user.role in (models.UserRole.admin, models.UserRole.staff):
        return True
    return customer.user_id == user.id


@router.get("", response_model=List[schemas.CustomerOut])
def list_customers(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    query = db.query(models.Customer)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Customer.name.ilike(like))
    return query.order_by(models.Customer.name).all()


@router.post("", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: schemas.CustomerCreate, db: Session = Depends(get_db), _user=Depends(require_staff)
):
    customer = models.Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/me", response_model=schemas.CustomerOut)
def get_my_customer_profile(
    db: Session = Depends(get_db), user: models.Profile = Depends(get_current_user)
):
    """Used by the customer-facing 'My Account' page."""
    customer = db.query(models.Customer).filter(models.Customer.user_id == user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="No customer profile linked to this account")
    return customer


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer or not _visible_to(user, customer):
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: int,
    payload: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}/history", response_model=List[schemas.SaleOut])
def customer_history(
    customer_id: int,
    db: Session = Depends(get_db),
    user: models.Profile = Depends(get_current_user),
):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer or not _visible_to(user, customer):
        raise HTTPException(status_code=404, detail="Customer not found")

    from .sales import _to_out as sale_to_out  # local import avoids a circular import

    sales = (
        db.query(models.Sale)
        .filter(models.Sale.customer_id == customer_id)
        .order_by(models.Sale.sale_date.desc())
        .all()
    )
    return [sale_to_out(s) for s in sales]


@router.post("/{customer_id}/credit-payment", response_model=schemas.CustomerOut)
def record_credit_payment(
    customer_id: int,
    payload: schemas.CreditPayment,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    """Record a payment against a customer's outstanding credit balance."""
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if payload.amount > customer.credit_balance:
        raise HTTPException(
            status_code=400,
            detail="Payment exceeds the customer's outstanding balance",
        )
    payment_remaining = round(payload.amount, 2)

    # Apply the customer's payment to the oldest outstanding credit
    # invoices first. This keeps invoice payment status synchronized
    # with the customer's aggregate credit balance.
    credit_sales = (
        db.query(models.Sale)
        .filter(
            models.Sale.customer_id == customer_id,
            models.Sale.payment_method == models.PaymentMethod.credit,
            models.Sale.amount_paid < models.Sale.total_amount,
        )
        .order_by(models.Sale.sale_date.asc(), models.Sale.id.asc())
        .all()
    )

    for sale in credit_sales:
        if payment_remaining <= 0:
            break

        outstanding = round(sale.total_amount - sale.amount_paid, 2)
        if outstanding <= 0:
            continue

        applied = min(payment_remaining, outstanding)
        sale.amount_paid = round(sale.amount_paid + applied, 2)

        if sale.amount_paid >= sale.total_amount:
            sale.amount_paid = round(sale.total_amount, 2)
            sale.payment_status = models.PaymentStatus.paid
        elif sale.amount_paid > 0:
            sale.payment_status = models.PaymentStatus.partial
        else:
            sale.payment_status = models.PaymentStatus.unpaid

        payment_remaining = round(payment_remaining - applied, 2)

    customer.credit_balance = round(customer.credit_balance - payload.amount, 2)

    # Avoid tiny floating-point residue such as -0.00000001.
    if abs(customer.credit_balance) < 0.01:
        customer.credit_balance = 0.0

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)
):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.sales:
        raise HTTPException(
            status_code=400, detail="Cannot delete a customer with recorded sales"
        )
    db.delete(customer)
    db.commit()
    return None
