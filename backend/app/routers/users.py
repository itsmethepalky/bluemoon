"""
Staff & admin account management (admin-only).

Login identities live in Supabase Auth, so creating/editing/disabling a
"user" here means calling the Supabase Admin Auth API (which needs the
SECRET service_role key - see app/supabase_client.py) in addition to
updating our own `profiles` table for app-specific fields like role.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin
from ..supabase_client import supabase_admin

router = APIRouter(prefix="/api/users", tags=["Staff Accounts"])


@router.get("", response_model=List[schemas.ProfileOut])
def list_users(
    role: Optional[models.UserRole] = None,
    db: Session = Depends(get_db),
    _admin: models.Profile = Depends(require_admin),
):
    """
    List staff/admin accounts only.

    Customer profiles are intentionally excluded from this endpoint.
    If a role is supplied, it can only further narrow the result to
    admin/staff roles.
    """
    staff_roles = [
        models.UserRole.admin,
        models.UserRole.staff,
    ]

    query = db.query(models.Profile).filter(
        models.Profile.role.in_(staff_roles)
    )

    if role:
        # A customer role must never make it into Staff Accounts.
        if role not in staff_roles:
            return []

        query = query.filter(models.Profile.role == role)

    return query.order_by(models.Profile.created_at).all()


@router.post(
    "",
    response_model=schemas.ProfileOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    _admin: models.Profile = Depends(require_admin),
):
    """
    Creates a real Supabase Auth login (email/password) for a staff or
    admin account.

    The on_auth_user_created DB trigger creates the matching profiles row
    automatically - we just fetch it back.
    """

    # Prevent accidentally creating a customer through the Staff Accounts
    # endpoint.
    if payload.role not in (
        models.UserRole.admin,
        models.UserRole.staff,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff Accounts can only create staff or admin accounts.",
        )

    try:
        result = supabase_admin.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": payload.full_name,
                    "role": payload.role.value,
                    "phone": payload.phone,
                },
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not create the account: {exc}",
        )

    new_id = result.user.id

    # The trigger committed in a separate transaction.
    db.expire_all()

    profile = (
        db.query(models.Profile)
        .filter(models.Profile.id == new_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=500,
            detail=(
                "Auth user was created but its profile row was not found. "
                "Check that the on_auth_user_created trigger is installed."
            ),
        )

    return profile


@router.put("/{user_id}", response_model=schemas.ProfileOut)
def update_user(
    user_id: str,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _admin: models.Profile = Depends(require_admin),
):
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.id == user_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    # Do not allow the Staff Accounts endpoint to convert a staff/admin
    # account into a customer account.
    if payload.role is not None and payload.role == models.UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A staff account cannot be changed to a customer account.",
        )

    data = payload.model_dump(exclude_unset=True)

    password = data.pop("password", None)
    new_email = data.pop("email", None)

    # Anything that touches the Supabase Auth identity itself goes through
    # the admin API; everything else is our own profiles row.
    auth_updates = {}

    if password:
        auth_updates["password"] = password

    if new_email and new_email != profile.email:
        auth_updates["email"] = new_email

    if auth_updates:
        try:
            supabase_admin.auth.admin.update_user_by_id(
                str(profile.id),
                auth_updates,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not update the account: {exc}",
            )

        if new_email:
            profile.email = new_email

    for field, value in data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: models.Profile = Depends(require_admin),
):
    if user_id == str(admin.id):
        raise HTTPException(
            status_code=400,
            detail="You cannot disable your own account",
        )

    profile = (
        db.query(models.Profile)
        .filter(models.Profile.id == user_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    profile.is_active = False
    db.commit()

    # Also lock them out at the Supabase Auth layer.
    try:
        supabase_admin.auth.admin.update_user_by_id(
            str(profile.id),
            {"ban_duration": "876000h"},
        )
    except Exception:
        # profiles.is_active=False already blocks our API.
        pass

    return None