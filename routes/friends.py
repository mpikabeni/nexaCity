from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.friend_service import FriendService


router = APIRouter(
    prefix="/friends",
    tags=["Friends"],
)


class FriendRequestCreate(BaseModel):
    sender_id: int
    receiver_id: int


class FriendRequestResponse(BaseModel):
    user_id: int
    request_id: int
    accept: bool


class RemoveFriendRequest(BaseModel):
    user_id: int
    friend_id: int


class BlockPlayerRequest(BaseModel):
    user_id: int
    blocked_user_id: int


@router.get("/{user_id}")
async def get_friends(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    friends = await FriendService.get_friends(
        db,
        user_id,
    )

    return {
        "user_id": user_id,
        "friends": [
            {
                "user_id": friend.id,
                "username": friend.username,
                "first_name": friend.first_name,
                "last_name": friend.last_name,
                "online": friend.online,
            }
            for friend in friends
        ],
    }


@router.post("/request")
async def send_friend_request(
    data: FriendRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    request = await FriendService.send_request(
        db=db,
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
    )

    if request is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to send friend request",
        )

    return {
        "status": "request_sent",
        "request_id": request.id,
        "sender_id": request.sender_id,
        "receiver_id": request.receiver_id,
    }


@router.post("/request/respond")
async def respond_to_friend_request(
    data: FriendRequestResponse,
    db: AsyncSession = Depends(get_db),
):
    result = await FriendService.respond_request(
        db=db,
        user_id=data.user_id,
        request_id=data.request_id,
        accept=data.accept,
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Unable to respond to friend request",
        )

    return {
        "status": "request_accepted" if data.accept else "request_rejected",
        "request_id": data.request_id,
    }


@router.delete("/remove")
async def remove_friend(
    data: RemoveFriendRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await FriendService.remove_friend(
        db=db,
        user_id=data.user_id,
        friend_id=data.friend_id,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Friendship not found",
        )

    return {
        "status": "friend_removed",
        "user_id": data.user_id,
        "friend_id": data.friend_id,
    }


@router.post("/block")
async def block_player(
    data: BlockPlayerRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await FriendService.block_player(
        db=db,
        user_id=data.user_id,
        blocked_user_id=data.blocked_user_id,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Unable to block player",
        )

    return {
        "status": "player_blocked",
        "blocked_user_id": data.blocked_user_id,
}
