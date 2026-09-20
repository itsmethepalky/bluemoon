"""
Authentication now lives in Supabase Auth. This module validates the
access token a client sends us (obtained via supabase-js sign in / sign up)
by asking Supabase's Auth server to confirm it's valid, rather than
verifying a JWT signature ourselves. This is slightly slower per-request
than local verification but needs no shared secret / JWKS handling in the
backend and transparently supports token refresh, revocation, etc.
"""
from typing import Optional

from .supabase_client import supabase_anon


class InvalidTokenError(Exception):
    pass


def get_auth_user(access_token: str):
    """Validate a Supabase access token and return the Supabase auth user.

    Raises InvalidTokenError if the token is missing/expired/invalid.
    """
    if not access_token:
        raise InvalidTokenError("Missing token")
    try:
        response = supabase_anon.auth.get_user(access_token)
    except Exception as exc:  # supabase-py raises AuthApiError on bad tokens
        raise InvalidTokenError(str(exc)) from exc

    if not response or not response.user:
        raise InvalidTokenError("Invalid or expired token")
    return response.user
