# fastapi_app/code_editor/router.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/editor/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Process and broadcast data here
            await websocket.send_text(f"Received in room {room_id}: {data}")
    except WebSocketDisconnect:
        print(f"Client disconnected from room {room_id}")
