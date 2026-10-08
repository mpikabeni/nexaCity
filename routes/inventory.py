from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.inventory import InventoryItem
from models.user import User
from services.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


# ============================================================
# SCHEMAS
# ============================================================

class InventoryItemRequest(BaseModel):
    item_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    item_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    quantity: int = Field(
        ...,
        gt=0,
    )


class RemoveItemRequest(BaseModel):
    item_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    quantity: int = Field(
        ...,
        gt=0,
    )


# ============================================================
# HELPERS
# ============================================================

async def get_inventory_item(
    user_id: int,
    item_id: str,
    db: AsyncSession,
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.user_id == user_id,
            InventoryItem.item_id == item_id,
        )
    )

    return result.scalar_one_or_none()


def serialize_item(item: InventoryItem) -> dict:
    return {
        "id": item.id,
        "item_id": item.item_id,
        "item_type": item.item_type,
        "quantity": item.quantity,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


# ============================================================
# MY INVENTORY
# ============================================================

@router.get("/me")
async def get_my_inventory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne l'inventaire du joueur connecté.
    """

    result = await db.execute(
        select(InventoryItem)
        .where(
            InventoryItem.user_id == current_user.id
        )
        .order_by(
            InventoryItem.created_at.asc()
        )
    )

    items = result.scalars().all()

    return {
        "status": "success",
        "user_id": current_user.id,
        "items": [
            serialize_item(item)
            for item in items
        ],
    }


# ============================================================
# GET ONE ITEM
# ============================================================

@router.get("/me/{item_id}")
async def get_my_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne un objet précis de l'inventaire.
    """

    item = await get_inventory_item(
        current_user.id,
        item_id,
        db,
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Objet introuvable dans l'inventaire.",
        )

    return {
        "status": "success",
        "item": serialize_item(item),
    }


# ============================================================
# HAS ITEM
# ============================================================

@router.get("/me/{item_id}/has")
async def has_my_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Vérifie si le joueur possède un objet.
    """

    item = await get_inventory_item(
        current_user.id,
        item_id,
        db,
    )

    return {
        "status": "success",
        "item_id": item_id,
        "has_item": item is not None and item.quantity > 0,
        "quantity": item.quantity if item else 0,
    }


# ============================================================
# ADD ITEM
# ============================================================

@router.post("/me/add")
async def add_item(
    data: InventoryItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ajoute un objet à l'inventaire.

    Dans la version finale, cette opération sera appelée
    par les services serveur après une récompense, mission,
    achat ou événement autorisé.
    """

    item = await get_inventory_item(
        current_user.id,
        data.item_id,
        db,
    )

    if item:

        item.quantity += data.quantity

        await db.commit()
        await db.refresh(item)

        return {
            "status": "success",
            "message": "Objet ajouté.",
            "item": serialize_item(item),
        }

    item = InventoryItem(
        user_id=current_user.id,
        item_id=data.item_id,
        item_type=data.item_type,
        quantity=data.quantity,
    )

    db.add(item)

    await db.commit()
    await db.refresh(item)

    return {
        "status": "success",
        "message": "Objet ajouté.",
        "item": serialize_item(item),
    }


# ============================================================
# REMOVE ITEM
# ============================================================

@router.post("/me/remove")
async def remove_item(
    data: RemoveItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retire une quantité d'un objet.
    """

    item = await get_inventory_item(
        current_user.id,
        data.item_id,
        db,
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Objet introuvable.",
        )

    if item.quantity < data.quantity:
        raise HTTPException(
            status_code=400,
            detail="Quantité insuffisante.",
        )

    item.quantity -= data.quantity

    if item.quantity <= 0:
        await db.delete(item)

        await db.commit()

        return {
            "status": "success",
            "message": "Objet retiré de l'inventaire.",
            "item_id": data.item_id,
            "quantity": 0,
        }

    await db.commit()
    await db.refresh(item)

    return {
        "status": "success",
        "message": "Objet retiré.",
        "item": serialize_item(item),
    }
