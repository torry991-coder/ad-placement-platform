"""JWT authentication module.

Provides token creation / verification and FastAPI auth endpoints.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.models.user import User

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────
# Using pbkdf2_sha256 instead of bcrypt to avoid Windows bcrypt issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# ── Security scheme ───────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


# ── JWT helpers ───────────────────────────────────────────────
def _get_jwt_secret() -> str:
    """Return JWT secret from env/config, or generate a random one."""
    env_secret = os.environ.get("JWT_SECRET_KEY", "")
    if env_secret:
        return env_secret
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    # Fallback: random hex (persists only for this process lifetime)
    return secrets.token_hex(32)


JWT_SECRET = _get_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT for the given user_id."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[int]:
    """Verify a JWT and return the user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", ""))
        return user_id
    except (JWTError, ValueError):
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: extract and validate the current user from JWT."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


# ── Schemas ───────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Router ────────────────────────────────────────────────────
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate with username/password and receive a JWT."""
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()
    if user is None or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user account."""
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    # Create user
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ── Helper: create default admin ──────────────────────────────
async def ensure_default_admin(db: AsyncSession) -> None:
    """Create a default admin user (admin / admin123) if no users exist."""
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # users already exist
    admin = User(
        username="admin",
        email="admin@adplatform.local",
        hashed_password=pwd_context.hash("admin123"),
        is_active=True,
    )
    db.add(admin)
    await db.flush()
