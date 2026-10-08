from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.user import User
from services.auth_service import decode_access_token


# ============================================================
# HTTP BEARER
# ============================================================

security = HTTPBearer(
    auto_error=False
)


# ============================================================
# CURRENT USER
# ============================================================

async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Récupère l'utilisateur connecté à partir du JWT.

    Header attendu :

    Authorization: Bearer <JWT>
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    user_id = payload.get("user_id")

    if user_id is None:
        user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identité utilisateur absente.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identité utilisateur invalide.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé.",
        )

    return user


# ============================================================
# CURRENT USER ID
# ============================================================

async def get_current_user_id(
    current_user: User = Depends(get_current_user),
) -> int:
    """
    Retourne uniquement l'ID interne du joueur connecté.
    """

    return current_user.id


# ============================================================
# CURRENT USER ROLE
# ============================================================

async def get_current_user_role(
    current_user: User = Depends(get_current_user),
) -> str:
    """
    Retourne le rôle du joueur connecté.
    """

    return current_user.role


# ============================================================
# ROLE CHECKER
# ============================================================

def require_roles(*allowed_roles: str):
    """
    Crée une dépendance permettant de limiter une route
    à certains rôles.

    Exemple :

        current_user: User = Depends(
            require_roles("ADMIN", "OWNER")
        )
    """

    async def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes.",
            )

        return current_user

    return role_dependency


# ============================================================
# ADMIN
# ============================================================

async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:

    allowed_roles = {
        "MODERATOR",
        "ADMIN",
        "SUPER_ADMIN",
        "OWNER",
    }

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis.",
        )

    return current_user


# ============================================================
# SUPER ADMIN
# ============================================================

async def get_current_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role not in {
        "SUPER_ADMIN",
        "OWNER",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès Super Admin requis.",
        )

    return current_user


# ============================================================
# OWNER
# ============================================================

async def get_current_owner(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès propriétaire requis.",
        )

    return current_user
