import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import get_auth_user, InvalidTokenError

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Profile:
    """Validate the Supabase access token and return our local Profile row.

    Login/signup/token issuance are handled entirely by Supabase Auth on
    the frontend (supabase-js). This dependency only verifies the token
    Supabase issued and resolves it to app-specific data (role, etc.).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        auth_user = get_auth_user(credentials.credentials)
    except InvalidTokenError:
        raise credentials_exception

    user_uuid = uuid.UUID(str(auth_user.id))
    profile = db.query(models.Profile).filter(models.Profile.id == user_uuid).first()

    if profile is None:
        # Safety net: the `on_auth_user_created` trigger normally creates
        # this row instantly on sign-up. Auto-heal if it's ever missing.
        metadata = auth_user.user_metadata or {}
        profile = models.Profile(
            id=user_uuid,
            full_name=metadata.get("full_name") or (auth_user.email or "").split("@")[0],
            email=auth_user.email,
            phone=metadata.get("phone"),
            role=models.UserRole(metadata.get("role", "customer")),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    if not profile.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return profile


def require_roles(*roles: models.UserRole):
    """Dependency factory: raises 403 unless the current user has one of `roles`."""

    def checker(current_user: models.Profile = Depends(get_current_user)) -> models.Profile:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return checker


# Convenience shorthands used throughout the routers
require_admin = require_roles(models.UserRole.admin)
require_staff = require_roles(models.UserRole.admin, models.UserRole.staff)
require_any = require_roles(models.UserRole.admin, models.UserRole.staff, models.UserRole.customer)
