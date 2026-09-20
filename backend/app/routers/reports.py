
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
            func.coalesce(func.sum(models.Sale.total_amount), 0),
        )
        .filter(models.Sale.sale_date >= today_start_utc)
        .first()
    )

    month_total = (
        db.query(func.coalesce(func.sum(models.Sale.total_amount), 0))
        .filter(models.Sale.sale_date >= month_start_utc)
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
    Total sales for each of the last `days` days, using Nepal dates.
    """

    today = nepal_today()
    start = today - timedelta(days=days - 1)
    start_utc = nepal_day_start_utc(start)

    rows = (
        db.query(
            func.date(models.Sale.sale_date).label("day"),
            func.coalesce(func.sum(models.Sale.total_amount), 0).label("total"),
        )
        .filter(models.Sale.sale_date >= start_utc)
        .group_by("day")
        .all()
    )

    # Database timestamps are UTC, so convert each sale date to Nepal
    # time before assigning it to a calendar day.
    totals_by_day = {}

    sales_query = (
        db.query(models.Sale.sale_date, models.Sale.total_amount)
        .filter(models.Sale.sale_date >= start_utc)
        .all()
    )

    for sale_date, amount in sales_query:
        if sale_date.tzinfo is None:
            sale_date = sale_date.replace(tzinfo=timezone.utc)

        local_day = sale_date.astimezone(NEPAL_TZ).date()
        totals_by_day[str(local_day)] = (
            totals_by_day.get(str(local_day), 0.0) + float(amount or 0)
        )

    points: List[schemas.SalesPoint] = []

    for i in range(days):
        day = start + timedelta(days=i)

        points.append(
            schemas.SalesPoint(
                label=day.strftime("%b %d"),
                total=round(totals_by_day.get(str(day), 0.0), 2),
            )
        )

    return points


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
    """

    query = db.query(models.SaleItem).join(models.Sale)

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

    revenue = 0.0
    cost = 0.0

    for item in query.all():
        # Only quantities that were actually kept by the customer count
        # toward revenue and estimated cost.
        net_quantity = max(
            0,
            item.quantity - item.returned_quantity,
        )

        if item.quantity <= 0 or net_quantity <= 0:
            continue

        net_ratio = net_quantity / item.quantity

        revenue += item.subtotal * net_ratio
        cost += (
            (item.product.cost_price if item.product else 0)
            * net_quantity
        )

    return {
        "revenue": round(revenue, 2),
        "estimated_cost": round(cost, 2),
        "estimated_profit": round(revenue - cost, 2),
    }
