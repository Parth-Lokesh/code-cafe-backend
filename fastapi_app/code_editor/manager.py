from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = []
        self.active_rooms[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_rooms[room_id].remove(websocket)
        if not self.active_rooms[room_id]:
            del self.active_rooms[room_id]

    async def broadcast(self, room_id: str, data: dict):
        for connection in self.active_rooms.get(room_id, []):
            await connection.send_json(data)
