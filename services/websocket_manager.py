from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.connections: dict[int, WebSocket] = {}
        self.instances: dict[str, set[int]] = defaultdict(set)

    async def connect(
        self,
        user_id: int,
        websocket: WebSocket,
        instance_id: str | None = None,
    ):
        await websocket.accept()

        self.connections[user_id] = websocket

        if instance_id:
            self.instances[instance_id].add(user_id)

    def disconnect(
        self,
        user_id: int,
        instance_id: str | None = None,
    ):
        self.connections.pop(user_id, None)

        if instance_id:
            players = self.instances.get(instance_id)

            if players:
                players.discard(user_id)

                if not players:
                    self.instances.pop(instance_id, None)

    async def send_to_player(
        self,
        user_id: int,
        data: dict[str, Any],
    ):
        websocket = self.connections.get(user_id)

        if websocket:
            await websocket.send_json(data)

    async def broadcast_to_instance(
        self,
        instance_id: str,
        data: dict[str, Any],
        exclude_user_id: int | None = None,
    ):
        players = self.instances.get(instance_id, set())

        for user_id in list(players):
            if user_id == exclude_user_id:
                continue

            websocket = self.connections.get(user_id)

            if websocket:
                try:
                    await websocket.send_json(data)
                except Exception:
                    self.disconnect(user_id, instance_id)

    async def broadcast_all(
        self,
        data: dict[str, Any],
        exclude_user_id: int | None = None,
    ):
        for user_id, websocket in list(self.connections.items()):
            if user_id == exclude_user_id:
                continue

            try:
                await websocket.send_json(data)
            except Exception:
                self.connections.pop(user_id, None)

    def get_online_count(self) -> int:
        return len(self.connections)

    def get_instance_players(
        self,
        instance_id: str,
    ) -> list[int]:
        return list(self.instances.get(instance_id, set()))


websocket_manager = WebSocketManager()
