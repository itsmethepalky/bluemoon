
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_staff

router = APIRouter(prefix="/api/reports", tags=["Reports & Dashboard"])

# Nepal local time
NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def nepal_today() -> date:
    """Return today's date in Nepal time."""
    return datetime.now(NEPAL_TZ).date()


def nepal_day_start_utc(day: date) -> datetime:
    """
    Convert Nepal midnight for a given date to a naive UTC datetime.

    Sale timestamps are stored using datetime.utcnow(), so database
    comparisons need UTC boundaries.
    """
    local_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=NEPAL_TZ)
    return local_start.astimezone(timezone.utc).replace(tzinfo=None)


@router.get("/dashboard", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _user=Depends(require_staff)):
    today = nepal_today()

    # Nepal midnight converted to UTC because sale_date is stored in UTC.
    today_start_utc = nepal_day_start_utc(today)
    month_start_utc = nepal_day_start_utc(today.replace(day=1))

    today_sales = (
        db.query(
            func.count(models.Sale.id),
            func.coalesce(func.sum(models.Sale.amount_paid), 0),
        )
        .filter(models.Sale.sale_date >= today_start_utc)
        .filter(models.Sale.status != models.SaleStatus.returned)
        .first()
    )

    month_total = (
        db.query(func.coalesce(func.sum(models.Sale.total_amount), 0))
        .filter(models.Sale.sale_date >= month_start_utc)
        .filter(models.Sale.status != models.SaleStatus.returned)
        .scalar()
    )

    low_stock_count = (
        db.query(func.count(models.Product.id))
        .filter(models.Product.is_active.is_(True))
        .filter(models.Product.stock_quantity <= models.Product.reorder_level)
        .scalar()
    )

    total_products = (
        db.query(func.count(models.Product.id))
        .filter(models.Product.is_active.is_(True))
        .scalar()
    )

    total_customers = db.query(func.count(models.Customer.id)).scalar()

    outstanding_credit = (
        db.query(func.coalesce(func.sum(models.Customer.credit_balance), 0))
        .scalar()
    )

    return schemas.DashboardSummary(
        today_sales_total=round(float(today_sales[1] or 0), 2),
        today_sales_count=int(today_sales[0] or 0),
        month_sales_total=round(float(month_total or 0), 2),
        low_stock_count=int(low_stock_count or 0),
        total_products=int(total_products or 0),
        total_customers=int(total_customers or 0),
        outstanding_credit=round(float(outstanding_credit or 0), 2),
    )


@router.get("/sales-trend", response_model=List[schemas.SalesPoint])
def sales_trend(
    days: int = 14,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    """
    Total sales for each of the last `days` days using Nepal calendar dates.

    Sale timestamps are stored as naive UTC datetimes, so PostgreSQL converts
    them to Asia/Kathmandu before grouping. This keeps the aggregation in the
    database without loading every sale into Python.
    """
    days = max(1, min(days, 90))

    today = nepal_today()
    start = today - timedelta(days=days - 1)
    start_utc = nepal_day_start_utc(start)

    # sale_date is stored as a naive UTC timestamp.
    # Convert UTC -> Nepal time before extracting the calendar date.
    nepal_day = func.date(
        func.timezone(
            "Asia/Kathmandu",
            func.timezone("UTC", models.Sale.sale_date),
        )
    )

    rows = (
        db.query(
            nepal_day.label("day"),
            func.coalesce(
                func.sum(models.Sale.total_amount),
                0,
            ).label("total"),
        )
        .filter(models.Sale.sale_date >= start_utc)
        .filter(models.Sale.status != models.SaleStatus.returned)
        .group_by(nepal_day)
        .all()
    )

    totals_by_day = {
        str(day): float(total or 0)
        for day, total in rows
    }

    return [
        schemas.SalesPoint(
            label=(start + timedelta(days=i)).strftime("%b %d"),
            total=round(
                totals_by_day.get(
                    str(start + timedelta(days=i)),
                    0.0,
                ),
                2,
            ),
        )
        for i in range(days)
    ]

@router.get("/top-products", response_model=List[schemas.TopProduct])
def top_products(
    limit: int = 5,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    rows = (
        db.query(
            models.Product.id,
            models.Product.name,
            func.coalesce(
                func.sum(
                    models.SaleItem.quantity - models.SaleItem.returned_quantity
                ),
                0,
            ).label("qty"),
            func.coalesce(
                func.sum(
                    models.SaleItem.subtotal
                    * (
                        models.SaleItem.quantity
                        - models.SaleItem.returned_quantity
                    )
                    / models.SaleItem.quantity
                ),
                0,
            ).label("revenue"),
        )
        .join(
            models.SaleItem,
            models.SaleItem.product_id == models.Product.id,
        )
        .group_by(models.Product.id, models.Product.name)
        .order_by(func.sum(models.SaleItem.quantity).desc())
        .limit(limit)
        .all()
    )

    return [
        schemas.TopProduct(
            product_id=r.id,
            product_name=r.name,
            quantity_sold=int(r.qty),
            revenue=round(float(r.revenue), 2),
        )
        for r in rows
    ]


@router.get("/inventory-status", response_model=List[schemas.InventoryStatusItem])
def inventory_status(
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    rows = (
        db.query(
            func.coalesce(models.Category.name, "Uncategorized").label("category"),
            func.coalesce(
                func.sum(
                    models.Product.stock_quantity * models.Product.unit_price
                ),
                0,
            ).label("value"),
            func.coalesce(
                func.sum(models.Product.stock_quantity),
                0,
            ).label("qty"),
        )
        .select_from(models.Product)
        .outerjoin(
            models.Category,
            models.Product.category_id == models.Category.id,
        )
        .filter(models.Product.is_active.is_(True))
        .group_by("category")
        .all()
    )

    return [
        schemas.InventoryStatusItem(
            category=r.category,
            stock_value=round(float(r.value), 2),
            quantity=int(r.qty),
        )
        for r in rows
    ]


@router.get("/profit")
def profit_report(
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(get_db),
    _user=Depends(require_staff),
):
    """
    Rough profit estimate: revenue from sale items minus each
    product's current cost price.

    PostgreSQL performs the aggregation so matching SaleItems are not
    loaded into Python.
    """

    query = (
        db.query(
            func.coalesce(
                func.sum(
                    models.SaleItem.subtotal
                    * func.greatest(
                        0,
                        models.SaleItem.quantity
                        - models.SaleItem.returned_quantity,
                    )
                    / func.nullif(
                        models.SaleItem.quantity,
                        0,
                    )
                ),
                0,
            ).label("revenue"),
            func.coalesce(
                func.sum(
                    func.coalesce(models.Product.cost_price, 0)
                    * func.greatest(
                        0,
                        models.SaleItem.quantity
                        - models.SaleItem.returned_quantity,
                    )
                ),
                0,
            ).label("cost"),
        )
        .select_from(models.SaleItem)
        .join(
            models.Sale,
            models.Sale.id == models.SaleItem.sale_id,
        )
        .outerjoin(
            models.Product,
            models.Product.id == models.SaleItem.product_id,
        )
    )

    if start:
        query = query.filter(
            models.Sale.sale_date >= nepal_day_start_utc(start)
        )

    if end:
        # Start of the following Nepal day, then use < instead of <=.
        next_day = end + timedelta(days=1)
        query = query.filter(
            models.Sale.sale_date < nepal_day_start_utc(next_day)
        )

    row = query.one()

    revenue = float(row.revenue or 0)
    cost = float(row.cost or 0)

    return {
        "revenue": round(revenue, 2),
        "estimated_cost": round(cost, 2),
        "estimated_profit": round(revenue - cost, 2),
    }
