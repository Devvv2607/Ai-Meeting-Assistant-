"""Supabase Auth (GoTrue) client — stores and verifies user credentials.

The backend keeps issuing its own JWTs for API sessions (get_current_user
and every protected route are unchanged); Supabase only owns the passwords.
The /api/v1/auth contract with the frontend is identical.

Enabled when SUPABASE_URL and SUPABASE_ANON_KEY are set. Tests set
SUPABASE_AUTH_DISABLED=1 to keep the suite on the local-hash path.
"""

import logging
import os

import requests

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class SupabaseAuthError(Exception):
    """A failed GoTrue call, with the upstream status and error code."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def enabled() -> bool:
    if os.getenv("SUPABASE_AUTH_DISABLED"):
        return False
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


def _post(path: str, payload: dict) -> dict:
    url = f"{settings.SUPABASE_URL}/auth/v1/{path}"
    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logger.error(f"Supabase auth request failed: {e}")
        raise SupabaseAuthError("Authentication service unreachable", 503)

    if response.ok:
        return response.json()

    try:
        body = response.json()
    except ValueError:
        body = {}
    message = (
        body.get("msg")
        or body.get("error_description")
        or body.get("message")
        or "Authentication failed"
    )
    error_code = str(body.get("error_code") or body.get("error") or "")
    logger.warning(
        f"Supabase auth error {response.status_code} ({error_code}): {message}"
    )
    raise SupabaseAuthError(message, response.status_code, error_code)


def sign_up(email: str, password: str, full_name: str = None) -> dict:
    """Create a Supabase auth user. Raises SupabaseAuthError on failure
    (error_code 'user_already_exists' when the email is taken)."""
    payload = {"email": email, "password": password}
    if full_name:
        payload["data"] = {"full_name": full_name}
    return _post("signup", payload)


def sign_in(email: str, password: str) -> dict:
    """Verify credentials via the password grant. Raises SupabaseAuthError
    on failure (error_code 'invalid_credentials' or 'email_not_confirmed')."""
    return _post(
        "token?grant_type=password", {"email": email, "password": password}
    )
