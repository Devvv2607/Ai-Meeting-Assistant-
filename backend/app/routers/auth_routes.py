from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from urllib.parse import urlsplit
from app.database import get_db
from app.schemas.auth_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenVerifyRequest,
    OAuthExchangeRequest,
    OAuthExchangeResponse,
)
from app.models.user import User
from app.utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
)
from app.utils.origins import origin_allowed
from app.services import supabase_auth
from app.services.supabase_auth import SupabaseAuthError
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _confirm_supabase_email(db: Session, email: str) -> None:
    """Mark a just-created Supabase auth user as email-confirmed.

    The project has GoTrue's "Confirm email" enabled, which blocks password
    logins until the emailed link is clicked. This app does its own signups
    with no mail flow, so confirm directly — the backend already connects to
    the same Supabase Postgres. No-op (best effort) if already confirmed.

    Commits on its own on purpose: if the caller's later writes fail, a
    confirmed-but-profileless Supabase account self-heals on next login via
    _ensure_local_user, whereas an unconfirmed account would be locked out.
    """
    try:
        db.execute(
            text(
                "UPDATE auth.users SET email_confirmed_at = now() "
                "WHERE email = :email AND email_confirmed_at IS NULL"
            ),
            {"email": email},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Could not auto-confirm Supabase email for {email}: {e}")


def _ensure_local_user(db: Session, email: str, full_name: str = None) -> User:
    """Get or create the local profile row for a Supabase-verified identity.

    Race-safe: two concurrent first logins can both see no row; the loser of
    the unique-email insert re-reads instead of surfacing a 500.
    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, password_hash="", full_name=full_name)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        return db.query(User).filter(User.email == email).first()


def _raise_for_signup_error(e: SupabaseAuthError) -> None:
    if e.error_code in ("user_already_exists", "email_exists"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if e.status_code == 429:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signups right now — try again in a few minutes",
        )
    if e.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=e.message
        )
    # Surface the real reason (e.g. weak_password) instead of masking it.
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


def _issue_token(user: User) -> dict:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires,
    )
    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
    }


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user

    Args:
        user: User registration data
        db: Database session

    Returns:
        Created user
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create credentials: Supabase Auth owns the password when configured;
        # otherwise fall back to the local bcrypt hash (dev/tests).
        if supabase_auth.enabled():
            try:
                signup = await supabase_auth.sign_up(
                    user.email, user.password, user.full_name
                )
            except SupabaseAuthError as e:
                _raise_for_signup_error(e)
            # Anti-enumeration 200: the email is already registered in
            # Supabase and NO credentials were set — do not report success.
            if supabase_auth.user_exists_response(signup):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            _confirm_supabase_email(db, user.email)
            hashed_password = ""  # password lives in Supabase Auth only
        else:
            hashed_password = hash_password(user.password)

        db_user = User(
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"New user registered: {user.email}")
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user

    Args:
        credentials: Login credentials
        db: Database session

    Returns:
        Access token
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    if supabase_auth.enabled():
        try:
            await supabase_auth.sign_in(credentials.email, credentials.password)
        except SupabaseAuthError as e:
            # Legacy fallback: accounts created before the Supabase switch
            # only have a local bcrypt hash. Verify locally, then migrate the
            # credentials into Supabase (best effort) so future logins hit it.
            legacy_ok = (
                user is not None
                and user.password_hash
                and verify_password(credentials.password, user.password_hash)
            )
            if legacy_ok:
                try:
                    await supabase_auth.sign_up(
                        credentials.email, credentials.password
                    )
                    logger.info(
                        f"Migrated legacy user to Supabase Auth: {credentials.email}"
                    )
                except SupabaseAuthError:
                    pass  # migration retries on the next login
                # Confirm even when sign_up said user_already_exists — a
                # previous migration may have created the account without
                # managing to confirm it (idempotent).
                _confirm_supabase_email(db, credentials.email)
            elif e.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts — try again in a few minutes",
                )
            elif e.status_code >= 500:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable, try again shortly",
                )
            elif e.error_code == "email_not_confirmed":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not confirmed — check your inbox for the confirmation link",
                )
            else:
                logger.warning(f"Failed login attempt for user: {credentials.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

        if user is None:
            # Supabase verified the credentials but the profile row is missing
            # (e.g. user was created directly in Supabase) — create it now.
            user = _ensure_local_user(db, credentials.email)
    else:
        if not user:
            logger.warning(f"Login attempt with non-existent email: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not verify_password(credentials.password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

    return _issue_token(user)


@router.get("/google/start")
async def google_start(redirect_to: str = Query(...)):
    """Kick off Google sign-in: 302 to Supabase's OAuth authorize endpoint.

    Supabase redirects the browser back to `redirect_to` (the frontend's
    /auth/callback page) with tokens in the URL fragment. The target origin
    must be an allowed frontend origin so tokens can't be bounced to an
    attacker-controlled site.
    """
    if not supabase_auth.enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured (Supabase Auth disabled)",
        )
    parts = urlsplit(redirect_to)
    origin = f"{parts.scheme}://{parts.netloc}"
    if parts.scheme not in ("http", "https") or not origin_allowed(origin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_to is not an allowed frontend origin",
        )
    return RedirectResponse(
        supabase_auth.authorize_url("google", redirect_to),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/google/exchange", response_model=OAuthExchangeResponse)
async def google_exchange(
    payload: OAuthExchangeRequest, db: Session = Depends(get_db)
):
    """Trade the Supabase access token from the OAuth redirect for this
    backend's own JWT (the same token every other endpoint expects)."""
    try:
        supabase_user = await supabase_auth.get_user(payload.access_token)
    except SupabaseAuthError as e:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if e.status_code >= 500
                else status.HTTP_401_UNAUTHORIZED
            ),
            detail="Google sign-in could not be verified" if e.status_code < 500
            else "Authentication service unavailable, try again shortly",
        )

    email = supabase_user.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account has no email",
        )
    metadata = supabase_user.get("user_metadata") or {}
    full_name = metadata.get("full_name") or metadata.get("name")

    user = _ensure_local_user(db, email, full_name)
    token = _issue_token(user)
    return {**token, "email": user.email, "full_name": user.full_name}


@router.post("/verify-token")
async def verify_token_endpoint(payload: TokenVerifyRequest):
    """Verify JWT token

    Args:
        payload: JSON body carrying the JWT to verify

    Returns:
        Token validity and claims
    """
    token_payload = verify_token(payload.token)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {
        "valid": True,
        "user_id": token_payload.get("user_id"),
        "email": token_payload.get("sub"),
    }
