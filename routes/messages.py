from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.message_service import MessageService


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


class SendMessageRequest(BaseModel):
    sender_id: int
    receiver_id: int
    content: str = Field(min_length=1, max_length=2000)


class ReadMessagesRequest(BaseModel):
    user_id: int
    other_user_id: int


class DeleteMessageRequest(BaseModel):
    user_id: int
    message_id: int


@router.post("/send")
async def send_message(
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    message = await MessageService.send_message(
        db=db,
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        content=content,
    )

    if message is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to send message",
        )

    return {
        "status": "message_sent",
        "message": {
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "created_at": message.created_at,
        },
    }


@router.get("/conversation/{user_id}/{other_user_id}")
async def get_conversation(
    user_id: int,
    other_user_id: int,
    db: AsyncSession = Depends(get_db),
):
    messages = await MessageService.get_conversation(
        db=db,
        user_id=user_id,
        other_user_id=other_user_id,
    )

    return {
        "user_id": user_id,
        "other_user_id": other_user_id,
        "messages": [
            {
                "id": message.id,
                "sender_id": message.sender_id,
                "receiver_id": message.receiver_id,
                "content": message.content,
                "is_read": message.is_read,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


@router.post("/read")
async def mark_messages_as_read(
    data: ReadMessagesRequest,
    db: AsyncSession = Depends(get_db),
):
    count = await MessageService.mark_as_read(
        db=db,
        user_id=data.user_id,
        other_user_id=data.other_user_id,
    )

    return {
        "status": "messages_read",
        "updated_count": count,
    }


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await MessageService.delete_message(
        db=db,
        user_id=user_id,
        message_id=message_id,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Message not found or not owned by player",
        )

    return {
        "status": "message_deleted",
        "message_id": message_id,
}
