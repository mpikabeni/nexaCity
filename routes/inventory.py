from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.inventory_service import InventoryService


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


class ItemRequest(BaseModel):
    user_id: int
    item_id: str = Field(min_length=1, max_length=100)
    item_type: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)


@router.get("/{user_id}")
async def get_inventory(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    items = await InventoryService.get_inventory(
        db,
        user_id,
    )

    return {
        "user_id": user_id,
        "items": [
            {
                "id": item.id,
                "item_id": item.item_id,
                "item_type": item.item_type,
                "quantity": item.quantity,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ],
    }


@router.get("/{user_id}/{item_id}")
async def get_item(
    user_id: int,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    item = await InventoryService.get_item(
        db,
        user_id,
        item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )

    return {
        "id": item.id,
        "item_id": item.item_id,
        "item_type": item.item_type,
        "quantity": item.quantity,
    }


@router.post("/add")
async def add_item(
    data: ItemRequest,
    db: AsyncSession = Depends(get_db),
):
    item = await InventoryService.add_item(
        db=db,
        user_id=data.user_id,
        item_id=data.item_id,
        item_type=data.item_type,
        quantity=data.quantity,
    )

    return {
        "status": "item_added",
        "item": {
            "id": item.id,
            "item_id": item.item_id,
            "item_type": item.item_type,
            "quantity": item.quantity,
        },
    }


@router.post("/remove")
async def remove_item(
    data: ItemRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await InventoryService.remove_item(
        db=db,
        user_id=data.user_id,
        item_id=data.item_id,
        quantity=data.quantity,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Unable to remove item or insufficient quantity",
        )

    return {
        "status": "item_removed",
        "item_id": data.item_id,
        "quantity": data.quantity,
    }


@router.get("/has/{user_id}/{item_id}")
async def has_item(
    user_id: int,
    item_id: str,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
):
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero",
        )

    has_item = await InventoryService.has_item(
        db,
        user_id,
        item_id,
        quantity,
    )

    return {
        "user_id": user_id,
        "item_id": item_id,
        "quantity_required": quantity,
        "has_item": has_item,
}
