from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import hashlib
import bcrypt

logger = logging.getLogger(__name__)

# Password hashing - disable max_password_size validation since we pre-hash with SHA256
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
security = HTTPBearer()


def _hash_password_sha256(password: str) -> str:
    """Hash password with SHA256 first to handle bcrypt's 72-byte limit"""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash password using SHA256 + bcrypt"""
    # First hash with SHA256 to ensure we don't exceed bcrypt's 72-byte limit
    # SHA256 always produces 64-byte hex string, well under bcrypt's 72-byte limit
    sha_hash = _hash_password_sha256(password)
    
    # Use bcrypt directly with 12 rounds for better security control
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(sha_hash.encode(), salt)
    return hashed.decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using SHA256 + bcrypt"""
    try:
        # Hash the plain password with SHA256 first, then verify with bcrypt
        sha_hash = _hash_password_sha256(plain_password)
        return bcrypt.checkpw(sha_hash.encode(), hashed_password.encode())
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    email = payload.get("sub")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Import here to avoid circular imports
    from app.models.user import User
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    finally:
        db.close()
