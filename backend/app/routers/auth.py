from fastapi import APIRouter, Depends

from .. import models, schemas
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# NOTE: there is no /register or /login endpoint here anymore. Sign-up and
# sign-in are handled directly by Supabase Auth via supabase-js on the
# frontend (see frontend/js/api.js). A Postgres trigger automatically
# creates the matching `profiles` (and, for customers, `customers`) row
# the moment someone signs up - see database/migrations/002_signup_trigger*.
# This endpoint just reports who the currently-authenticated user is,
# resolved from whatever Supabase access token they send us.


@router.get("/me", response_model=schemas.ProfileOut)
def read_me(current_user: models.Profile = Depends(get_current_user)):
    return current_user
