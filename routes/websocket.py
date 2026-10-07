from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_manager import websocket_manager


router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
):
    instance_id = websocket.query_params.get("instance_id")

    await websocket_manager.connect(
        user_id=user_id,
        websocket=websocket,
        instance_id=instance_id,
    )

    try:
        await websocket_manager.broadcast_to_instance(
            instance_id or "global",
            {
                "type": "player_connected",
                "user_id": user_id,
            },
            exclude_user_id=user_id,
        )

        while True:
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                })

            elif message_type == "player_position":
                await websocket_manager.broadcast_to_instance(
                    instance_id or "global",
                    {
                        "type": "player_position",
                        "user_id": user_id,
                        "position": {
                            "x": data.get("x", 0),
                            "y": data.get("y", 0),
                            "z": data.get("z", 0),
                            "rotation_y": data.get(
                                "rotation_y",
                                0,
                            ),
                        },
                    },
                    exclude_user_id=user_id,
                )

            elif message_type == "chat_message":
                receiver_id = data.get("receiver_id")
                content = data.get("content", "").strip()

                if receiver_id and content:
                    await websocket_manager.send_to_player(
                        int(receiver_id),
                        {
                            "type": "chat_message",
                            "sender_id": user_id,
                            "content": content,
                        },
                    )

    except WebSocketDisconnect:
        websocket_manager.disconnect(
            user_id=user_id,
            instance_id=instance_id,
        )

        await websocket_manager.broadcast_to_instance(
            instance_id or "global",
            {
                "type": "player_disconnected",
                "user_id": user_id,
            },
        )

    except Exception:
        websocket_manager.disconnect(
            user_id=user_id,
            instance_id=instance_id,
)
