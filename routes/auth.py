import hashlib
import hmac
import json
import time
from datetime import datetime
from urllib.parse import parse_qsl

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.connection import get_db
from models.user import User
from services.auth_dependencies import get_current_user
from services.auth_service import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# CONFIGURATION
# ============================================================

TELEGRAM_AUTH_MAX_AGE = 24 * 60 * 60


# ============================================================
# SCHEMAS
# ============================================================

class TelegramAuthRequest(BaseModel):
    init_data: str = Field(
        ...,
        min_length=1,
        description="Telegram Web App initData",
    )


# ============================================================
# TELEGRAM INIT DATA VERIFICATION
# ============================================================

def verify_telegram_init_data(
    init_data: str,
) -> dict:
    """
    Vérifie cryptographiquement les données envoyées
    par Telegram Web App.

    Telegram utilise :

        HMAC-SHA256

    pour signer les données.
    """

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="initData Telegram manquant.",
        )

    try:
        parsed_data = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True,
            )
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="initData Telegram invalide.",
        )

    received_hash = parsed_data.pop("hash", None)

    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature Telegram absente.",
        )

    # --------------------------------------------------------
    # Vérification de l'âge des données
    # --------------------------------------------------------

    auth_date_raw = parsed_data.get("auth_date")

    if not auth_date_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth_date Telegram absent.",
        )

    try:
        auth_date = int(auth_date_raw)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth_date Telegram invalide.",
        )

    current_time = int(time.time())

    if current_time - auth_date > TELEGRAM_AUTH_MAX_AGE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Les données Telegram ont expiré.",
        )

    if auth_date > current_time + 60:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Date Telegram invalide.",
        )

    # --------------------------------------------------------
    # Création du secret Telegram
    # --------------------------------------------------------

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.telegram_bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # --------------------------------------------------------
    # data-check-string
    # --------------------------------------------------------

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed_data.items())
    )

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    # --------------------------------------------------------
    # Comparaison sécurisée
    # --------------------------------------------------------

    if not hmac.compare_digest(
        calculated_hash,
        received_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature Telegram invalide.",
        )

    # --------------------------------------------------------
    # Lecture de l'utilisateur Telegram
    # --------------------------------------------------------

    telegram_user_raw = parsed_data.get("user")

    if not telegram_user_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur Telegram absent.",
        )

    try:
        telegram_user = json.loads(telegram_user_raw)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur Telegram invalide.",
        )

    telegram_id = telegram_user.get("id")

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant Telegram absent.",
        )

    return {
        "telegram_user": telegram_user,
        "auth_date": auth_date,
    }


# ============================================================
# TELEGRAM LOGIN
# ============================================================

@router.post("/telegram")
async def telegram_login(
    data: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Connexion/création automatique via Telegram Mini App.
    """

    telegram_data = verify_telegram_init_data(
        data.init_data
    )

    telegram_user = telegram_data["telegram_user"]

    telegram_id = int(
        telegram_user["id"]
    )

    username = telegram_user.get("username")
    first_name = telegram_user.get("first_name")
    last_name = telegram_user.get("last_name")

    language = telegram_user.get(
        "language_code",
        "en",
    )

    # --------------------------------------------------------
    # Recherche du joueur
    # --------------------------------------------------------

    result = await db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    # --------------------------------------------------------
    # Création du compte
    # --------------------------------------------------------

    if not user:

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            country=None,

            role="PLAYER",

            active=True,
            online=True,

            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(user)

        await db.commit()
        await db.refresh(user)

        is_new_user = True

    else:

        # ----------------------------------------------------
        # Mise à jour des informations Telegram
        # ----------------------------------------------------

        user.username = username
        user.first_name = first_name
        user.last_name = last_name

        if language:
            user.language = language

        user.active = True
        user.online = True
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        is_new_user = False

    # --------------------------------------------------------
    # JWT
    # --------------------------------------------------------

    access_token = create_access_token(
        user_id=user.id,
        telegram_id=user.telegram_id,
        role=user.role,
    )

    # --------------------------------------------------------
    # Réponse
    # --------------------------------------------------------

    return {
        "status": "success",

        "is_new_user": is_new_user,

        "access_token": access_token,
        "token_type": "bearer",

        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language": user.language,
            "country": user.country,
            "role": user.role,
            "active": user.active,
            "online": user.online,
        },
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get("/me")
async def get_authenticated_user(
    current_user: User = Depends(get_current_user),
):
    """
    Retourne le compte du joueur actuellement connecté.
    """

    return {
        "status": "success",

        "user": {
            "id": current_user.id,
            "telegram_id": current_user.telegram_id,
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "language": current_user.language,
            "country": current_user.country,
            "role": current_user.role,
            "active": current_user.active,
            "online": current_user.online,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Déconnecte le joueur côté serveur.
    """

    current_user.online = False
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "Déconnexion réussie.",
}
