"""Supabase Auth (GoTrue) client — stores and verifies user credentials.

The backend keeps issuing its own JWTs for API sessions (get_current_user
and every protected route are unchanged); Supabase only owns the passwords
and the Google OAuth flow. The /api/v1/auth contract with the frontend is
identical.

Enabled when SUPABASE_URL and SUPABASE_ANON_KEY are set. Tests set
SUPABASE_AUTH_DISABLED=1 to keep the suite on the local-hash path.
"""

import logging
import os

import httpx

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


def _url() -> str:
    # Prefer the live environment over the import-time Settings snapshot so a
    # var injected/changed after startup (tests, config reloads) is honored.
    return (os.getenv("SUPABASE_URL") or settings.SUPABASE_URL).rstrip("/")


def _key() -> str:
    return os.getenv("SUPABASE_ANON_KEY") or settings.SUPABASE_ANON_KEY


def enabled() -> bool:
    if os.getenv("SUPABASE_AUTH_DISABLED"):
        return False
    return bool(_url() and _key())


def authorize_url(provider: str, redirect_to: str) -> str:
    """The GoTrue OAuth entry point the browser should be redirected to."""
    from urllib.parse import quote
    return (
        f"{_url()}/auth/v1/authorize?provider={quote(provider)}"
        f"&redirect_to={quote(redirect_to, safe='')}"
    )


def _error_from(response: httpx.Response) -> SupabaseAuthError:
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
    # Older GoTrue /token responses use the OAuth2 shape
    # {"error": "invalid_grant", "error_description": "Email not confirmed"} —
    # normalize to the modern code so callers match on one value.
    if error_code == "invalid_grant" and "not confirmed" in str(message).lower():
        error_code = "email_not_confirmed"
    logger.warning(
        f"Supabase auth error {response.status_code} ({error_code}): {message}"
    )
    return SupabaseAuthError(message, response.status_code, error_code)


async def _request(method: str, path: str, *, json: dict = None,
                   bearer_token: str = None) -> dict:
    headers = {"apikey": _key(), "Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method, f"{_url()}/auth/v1/{path}", json=json, headers=headers
            )
    except httpx.HTTPError as e:
        logger.error(f"Supabase auth request failed: {e}")
        raise SupabaseAuthError("Authentication service unreachable", 503)

    if response.is_success:
        return response.json()
    raise _error_from(response)


async def sign_up(email: str, password: str, full_name: str = None) -> dict:
    """Create a Supabase auth user. Raises SupabaseAuthError on failure
    (error_code 'user_already_exists' when the email is taken).

    NOTE: when the email is already registered AND confirmed, GoTrue's
    anti-enumeration protection returns 200 with an obfuscated user whose
    `identities` list is empty instead of an error — callers must check
    `user_exists_response()` before treating the signup as successful.
    """
    payload = {"email": email, "password": password}
    if full_name:
        payload["data"] = {"full_name": full_name}
    return await _request("POST", "signup", json=payload)


def user_exists_response(signup_body: dict) -> bool:
    """True when a 200 signup response is GoTrue's obfuscated 'user already
    exists' reply (empty identities), meaning no credentials were set."""
    user_obj = signup_body.get("user") or signup_body
    return isinstance(user_obj, dict) and user_obj.get("identities") == []


async def sign_in(email: str, password: str) -> dict:
    """Verify credentials via the password grant. Raises SupabaseAuthError
    on failure (error_code 'invalid_credentials' or 'email_not_confirmed')."""
    return await _request(
        "POST", "token?grant_type=password",
        json={"email": email, "password": password},
    )


async def get_user(access_token: str) -> dict:
    """Resolve a Supabase access token (e.g. from the Google OAuth redirect)
    to its user object. Raises SupabaseAuthError if the token is invalid."""
    return await _request("GET", "user", bearer_token=access_token)
