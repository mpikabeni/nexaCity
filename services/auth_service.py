from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from config import settings


# ============================================================
# JWT CONFIGURATION
# ============================================================

ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.jwt_secret


# ============================================================
# CREATE ACCESS TOKEN
# ============================================================

def create_access_token(
    user_id: int,
    telegram_id: Optional[int] = None,
    role: Optional[str] = None,
) -> str:
    """
    Crée le token JWT utilisé par NEXA CITY.

    Le token contient :
    - user_id
    - telegram_id
    - role
    - date de création
    - date d'expiration
    """

    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "telegram_id": telegram_id,
        "role": role,

        "iat": now,
        "exp": expire,

        "type": "access",
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ============================================================
# DECODE ACCESS TOKEN
# ============================================================

def decode_access_token(token: str) -> dict:
    """
    Vérifie et décode un token JWT.

    Une exception est levée si :
    - le token est invalide
    - le token est expiré
    - la signature est incorrecte
    """

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError(
            "Type de token invalide."
        )

    return payload


# ============================================================
# GET USER ID FROM TOKEN
# ============================================================

def get_user_id_from_token(token: str) -> int:
    """
    Récupère l'identifiant interne du joueur depuis le JWT.
    """

    payload = decode_access_token(token)

    user_id = payload.get("user_id")

    if user_id is None:
        user_id = payload.get("sub")

    if user_id is None:
        raise jwt.InvalidTokenError(
            "Identifiant utilisateur absent du token."
        )

    try:
        return int(user_id)

    except (TypeError, ValueError):
        raise jwt.InvalidTokenError(
            "Identifiant utilisateur invalide."
        )


# ============================================================
# GET ROLE FROM TOKEN
# ============================================================

def get_role_from_token(token: str) -> Optional[str]:
    """
    Récupère le rôle du joueur depuis le JWT.
    """

    payload = decode_access_token(token)

    return payload.get("role")


# ============================================================
# CHECK TOKEN
# ============================================================

def is_token_valid(token: str) -> bool:
    """
    Retourne True si le JWT est valide.
    """

    try:
        decode_access_token(token)
        return True

    except jwt.PyJWTError:
        return False
