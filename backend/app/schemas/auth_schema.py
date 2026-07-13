from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""

    password: str


class UserLogin(BaseModel):
    """User login schema"""

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """User response schema"""

    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenVerifyRequest(BaseModel):
    """Body for POST /verify-token"""

    token: str


class OAuthExchangeRequest(BaseModel):
    """Body for POST /google/exchange — the Supabase access token from the
    OAuth redirect fragment."""

    access_token: str


class OAuthExchangeResponse(TokenResponse):
    """Token plus the profile fields the frontend stores locally."""

    email: EmailStr
    full_name: Optional[str] = None
