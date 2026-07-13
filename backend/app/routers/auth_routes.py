from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth_schema import UserCreate, UserLogin, UserResponse, TokenResponse
from app.models.user import User
from app.utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
)
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
                supabase_auth.sign_up(user.email, user.password, user.full_name)
            except SupabaseAuthError as e:
                if e.error_code == "user_already_exists" or e.status_code == 422:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered",
                    )
                raise HTTPException(
                    status_code=(
                        status.HTTP_502_BAD_GATEWAY
                        if e.status_code >= 500
                        else status.HTTP_400_BAD_REQUEST
                    ),
                    detail=e.message,
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
            supabase_auth.sign_in(credentials.email, credentials.password)
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
                    supabase_auth.sign_up(credentials.email, credentials.password)
                    _confirm_supabase_email(db, credentials.email)
                    logger.info(f"Migrated legacy user to Supabase Auth: {credentials.email}")
                except SupabaseAuthError:
                    pass  # migration retries on the next login
            elif e.status_code >= 500 or e.status_code == 503:
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
            user = User(email=credentials.email, password_hash="", full_name=None)
            db.add(user)
            db.commit()
            db.refresh(user)
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

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create tokens
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


@router.post("/verify-token")
async def verify_token_endpoint(token: str):
    """Verify JWT token

    Args:
        token: JWT token to verify

    Returns:
        Token validity and claims
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {
        "valid": True,
        "user_id": payload.get("user_id"),
        "email": payload.get("sub"),
    }
