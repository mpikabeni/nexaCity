from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.character import Character
from services.economy_service import EconomyService


router = APIRouter(
    prefix="/economy",
    tags=["Economy"],
)


class TransferRequest(BaseModel):
    sender_id: int
    receiver_id: int
    amount: float = Field(gt=0)


@router.get("/balance/{user_id}")
async def get_balance(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    balance = await EconomyService.get_balance(
        db,
        user_id,
    )

    if balance is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    return {
        "user_id": user_id,
        "balance": balance,
    }


@router.get("/transactions/{user_id}")
async def get_transactions(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from models.economy import Transaction

    limit = max(1, min(limit, 100))

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    transactions = result.scalars().all()

    return {
        "user_id": user_id,
        "transactions": [
            {
                "id": transaction.id,
                "amount": transaction.amount,
                "balance_before": transaction.balance_before,
                "balance_after": transaction.balance_after,
                "type": transaction.transaction_type,
                "description": transaction.description,
                "reference": transaction.reference,
                "created_at": transaction.created_at,
            }
            for transaction in transactions
        ],
    }


@router.post("/transfer")
async def transfer_money(
    data: TransferRequest,
    db: AsyncSession = Depends(get_db),
):
    # Vérification supplémentaire côté serveur.
    sender_result = await db.execute(
        select(Character).where(
            Character.user_id == data.sender_id
        )
    )

    sender = sender_result.scalar_one_or_none()

    receiver_result = await db.execute(
        select(Character).where(
            Character.user_id == data.receiver_id
        )
    )

    receiver = receiver_result.scalar_one_or_none()

    if sender is None or receiver is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    if not sender.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Sender cannot transfer money",
        )

    if not receiver.is_alive:
        raise HTTPException(
            status_code=403,
            detail="Receiver cannot receive money",
        )

    if sender.money < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance",
        )

    success = await EconomyService.transfer_money(
        db=db,
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        amount=data.amount,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Transfer failed",
        )

    return {
        "status": "transfer_completed",
        "sender_id": data.sender_id,
        "receiver_id": data.receiver_id,
        "amount": data.amount,
}
