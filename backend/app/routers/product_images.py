from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..supabase_client import supabase_admin

router = APIRouter(
    prefix="/api/product-images",
    tags=["Product Images"],
)

BUCKET = "product-images"

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 5 * 1024 * 1024


def require_staff_or_admin(user):
    if user.role not in (models.UserRole.admin, models.UserRole.staff):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required",
        )


@router.post("/{product_id}")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_staff_or_admin(user)

    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed",
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be 5 MB or smaller",
        )

    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[file.content_type]

    storage_path = f"products/{product_id}/{__import__('uuid').uuid4().hex}.{extension}"

    try:
        supabase_admin.storage.from_(BUCKET).upload(
            storage_path,
            data,
            {
                "content-type": file.content_type,
                "upsert": "false",
            },
        )

        image_url = supabase_admin.storage.from_(BUCKET).get_public_url(
            storage_path
        )

        has_primary = (
            db.query(models.ProductImage)
            .filter(
                models.ProductImage.product_id == product_id,
                models.ProductImage.is_primary.is_(True),
            )
            .first()
            is not None
        )

        image = models.ProductImage(
            product_id=product_id,
            storage_path=storage_path,
            image_url=image_url,
            is_primary=not has_primary,
            sort_order=(
                db.query(models.ProductImage)
                .filter(models.ProductImage.product_id == product_id)
                .count()
            ),
        )

        db.add(image)
        db.commit()
        db.refresh(image)

        return {
            "id": image.id,
            "product_id": image.product_id,
            "storage_path": image.storage_path,
            "image_url": image.image_url,
            "is_primary": image.is_primary,
            "sort_order": image.sort_order,
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()

        try:
            supabase_admin.storage.from_(BUCKET).remove([storage_path])
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload product image",
        ) from exc


@router.get("/{product_id}")
def list_product_images(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(models.Product)
        .filter(models.Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    images = (
        db.query(models.ProductImage)
        .filter(models.ProductImage.product_id == product_id)
        .order_by(
            models.ProductImage.is_primary.desc(),
            models.ProductImage.sort_order.asc(),
            models.ProductImage.id.asc(),
        )
        .all()
    )

    return [
        {
            "id": image.id,
            "image_url": image.image_url,
            "is_primary": image.is_primary,
            "sort_order": image.sort_order,
        }
        for image in images
    ]


@router.patch("/{image_id}/primary")
def set_primary_image(
    image_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_staff_or_admin(user)

    image = (
        db.query(models.ProductImage)
        .filter(models.ProductImage.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    db.query(models.ProductImage).filter(
        models.ProductImage.product_id == image.product_id
    ).update(
        {models.ProductImage.is_primary: False},
        synchronize_session=False,
    )

    image.is_primary = True

    db.commit()

    return {
        "message": "Primary image updated",
        "image_id": image.id,
    }


@router.delete("/{image_id}")
def delete_product_image(
    image_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_staff_or_admin(user)

    image = (
        db.query(models.ProductImage)
        .filter(models.ProductImage.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    storage_path = image.storage_path
    product_id = image.product_id
    was_primary = image.is_primary

    db.delete(image)
    db.commit()

    try:
        supabase_admin.storage.from_(BUCKET).remove([storage_path])
    except Exception:
        pass

    if was_primary:
        replacement = (
            db.query(models.ProductImage)
            .filter(models.ProductImage.product_id == product_id)
            .order_by(models.ProductImage.sort_order.asc())
            .first()
        )

        if replacement:
            replacement.is_primary = True
            db.commit()

    return {
        "message": "Product image deleted",
        "image_id": image_id,
    }
