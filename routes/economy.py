from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from models.economy import Transaction
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/economy",
    tags=["Economy"],
)


# ============================================================
# SCHEMAS
# ============================================================

class TransferRequest(BaseModel):
    receiver_user_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)


class MoneyRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: str | None = Field(
        default=None,
        max_length=255,
    )


# ============================================================
# HELPERS
# ============================================================

async def get_my_character(
    current_user: User,
    db: AsyncSession,
) -> Character:

    result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=404,
            detail="Aucun personnage créé.",
        )

    return character


def money_value(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(
            status_code=500,
            detail="Valeur monétaire invalide.",
        )


# ============================================================
# MY BALANCE
# ============================================================

@router.get("/balance")
async def get_my_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    character = await get_my_character(
        current_user,
        db,
    )

    return {
        "status": "success",
        "user_id": current_user.id,
        "character_id": character.id,
        "balance": character.money,
        "currency": "NEXA",
    }


# ============================================================
# MY TRANSACTIONS
# ============================================================

@router.get("/transactions")
async def get_my_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.user_id == current_user.id
        )
        .order_by(
            Transaction.timestamp.desc()
        )
    )

    transactions = result.scalars().all()

    return {
        "status": "success",
        "transactions": [
            {
                "id": transaction.id,
                "amount": transaction.amount,
                "balance_before": transaction.balance_before,
                "balance_after": transaction.balance_after,
                "type": transaction.type,
                "description": transaction.description,
                "reference": transaction.reference,
                "timestamp": transaction.timestamp,
            }
            for transaction in transactions
        ],
    }


# ============================================================
# TRANSFER MONEY
# ============================================================

@router.post("/transfer")
async def transfer_money(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.receiver_user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous transférer de l'argent à vous-même.",
        )

    amount = money_value(data.amount)

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Le montant doit être supérieur à zéro.",
        )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    sender_result = await db.execute(
        select(Character).where(
            Character.user_id == current_user.id
        )
    )

    sender = sender_result.scalar_one_or_none()

    if not sender:
        raise HTTPException(
            status_code=404,
            detail="Personnage expéditeur introuvable.",
        )

    # --------------------------------------------------------
    # DESTINATION
    # --------------------------------------------------------

    receiver_result = await db.execute(
        select(Character).where(
            Character.user_id == data.receiver_user_id
        )
    )

    receiver = receiver_result.scalar_one_or_none()

    if not receiver:
        raise HTTPException(
            status_code=404,
            detail="Personnage destinataire introuvable.",
        )

    # --------------------------------------------------------
    # VERIFICATION DU SOLDE
    # --------------------------------------------------------

    sender_balance = money_value(sender.money)

    if sender_balance < amount:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    receiver_balance = money_value(receiver.money)

    # --------------------------------------------------------
    # TRANSFERT
    # --------------------------------------------------------

    new_sender_balance = sender_balance - amount
    new_receiver_balance = receiver_balance + amount

    sender.money = float(new_sender_balance)
    receiver.money = float(new_receiver_balance)

    # --------------------------------------------------------
    # TRANSACTION EXPEDITEUR
    # --------------------------------------------------------

    sender_transaction = Transaction(
        user_id=current_user.id,
        amount=-float(amount),
        balance_before=float(sender_balance),
        balance_after=float(new_sender_balance),
        type="TRANSFER_SENT",
        description=(
            f"Transfert vers le joueur "
            f"{data.receiver_user_id}"
        ),
    )

    # --------------------------------------------------------
    # TRANSACTION DESTINATAIRE
    # --------------------------------------------------------

    receiver_transaction = Transaction(
        user_id=data.receiver_user_id,
        amount=float(amount),
        balance_before=float(receiver_balance),
        balance_after=float(new_receiver_balance),
        type="TRANSFER_RECEIVED",
        description=(
            f"Transfert reçu du joueur "
            f"{current_user.id}"
        ),
    )

    db.add(sender_transaction)
    db.add(receiver_transaction)

    await db.commit()

    await db.refresh(sender)
    await db.refresh(receiver)

    return {
        "status": "success",
        "message": "Transfert effectué.",

        "sender": {
            "user_id": current_user.id,
            "balance": sender.money,
        },

        "receiver": {
            "user_id": data.receiver_user_id,
            "balance": receiver.money,
        },

        "amount": float(amount),
    }


# ============================================================
# INTERNAL CREDIT
# ============================================================

@router.post("/credit")
async def credit_my_wallet(
    data: MoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crédit interne.

    Cette route sera principalement utilisée par les
    services serveur autorisés.

    Elle ne doit pas être utilisée comme système de
    création d'argent côté frontend.
    """

    character = await get_my_character(
        current_user,
        db,
    )

    amount = money_value(data.amount)

    balance_before = money_value(character.money)
    balance_after = balance_before + amount

    character.money = float(balance_after)

    transaction = Transaction(
        user_id=current_user.id,
        amount=float(amount),
        balance_before=float(balance_before),
        balance_after=float(balance_after),
        type="CREDIT",
        description=data.description or "Crédit interne",
    )

    db.add(transaction)

    await db.commit()

    return {
        "status": "success",
        "balance": character.money,
        "amount": float(amount),
    }


# ============================================================
# INTERNAL DEBIT
# ============================================================

@router.post("/debit")
async def debit_my_wallet(
    data: MoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Débit interne contrôlé par le serveur.
    """

    character = await get_my_character(
        current_user,
        db,
    )

    amount = money_value(data.amount)

    balance_before = money_value(character.money)

    if balance_before < amount:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant.",
        )

    balance_after = balance_before - amount

    character.money = float(balance_after)

    transaction = Transaction(
        user_id=current_user.id,
        amount=-float(amount),
        balance_before=float(balance_before),
        balance_after=float(balance_after),
        type="DEBIT",
        description=data.description or "Débit interne",
    )

    db.add(transaction)

    await db.commit()

    return {
        "status": "success",
        "balance": character.money,
        "amount": float(amount),
}
