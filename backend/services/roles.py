"""
User role & permissions system.

Roles:
  - admin: Full system access (manage users, view all campaigns)
  - advertiser: Manage own campaigns only
  - analyst: Read-only access to analytics and reports

Usage:
    from backend.services.roles import require_role, Role

    @router.get("/admin-only")
    async def admin_endpoint(user = Depends(get_current_user)):
        require_role(user, Role.ADMIN)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import Column, Integer, String, Enum as SAEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import Base


class Role(str, Enum):
    ADMIN = "admin"
    ADVERTISER = "advertiser"
    ANALYST = "analyst"


class UserRole(Base):
    """User role assignment table (separate from User for flexibility)."""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False, default=Role.ADVERTISER.value)


# ── Role-based access control ───────────────────────────────────────────

def get_user_role(user) -> Role:
    """Extract role from user object. Default to advertiser if not set."""
    if hasattr(user, "role") and user.role:
        try:
            return Role(user.role)
        except ValueError:
            pass
    return Role.ADVERTISER


def require_role(user, required: Role) -> None:
    """Raise 403 if user doesn't have the required role."""
    user_role = get_user_role(user)
    if user_role != required and user_role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {required.value} role",
        )


def require_any_role(user, *roles: Role) -> None:
    """Raise 403 if user has none of the required roles."""
    user_role = get_user_role(user)
    if user_role == Role.ADMIN:
        return  # admin bypasses all checks
    if user_role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of: {', '.join(r.value for r in roles)}",
        )


# ── Role helpers for DB ─────────────────────────────────────────────────

async def set_user_role(db: AsyncSession, user_id: int, role: Role) -> UserRole:
    """Set or update a user's role."""
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.role = role.value
    else:
        row = UserRole(user_id=user_id, role=role.value)
        db.add(row)
    await db.flush()
    return row


async def get_user_role_from_db(db: AsyncSession, user_id: int) -> Optional[Role]:
    """Get user role from database."""
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row:
        try:
            return Role(row.role)
        except ValueError:
            pass
    return None
