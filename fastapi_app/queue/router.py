from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi_app.queue.queue import enqueue_user, dequeue_users, get_queue_length
# fastapi_app/queue/matcher_sse.py
import asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse
import json
from fastapi_app.database.mongo import db

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from uuid import uuid4
import logging
import traceback
from fastapi import Request
# This holds active waiting clients
user_sse_connections = {}

router = APIRouter()


class QueueRequest(BaseModel):
    domain: str
    room_type: str
    user_id: str

@router.get("/queue/join")
async def sse_queue_listener(request: Request, user_id: str):
    event = asyncio.Event()
    user_sse_connections[user_id] = {"event": event, "room_id": None}

    async def event_generator():
        try:
            await event.wait()
            room_id = user_sse_connections[user_id]["room_id"]
            yield f"data: {json.dumps({'room_id': room_id})}\n\n"
        except asyncio.CancelledError:
            print(f"❌ Disconnected: {user_id}")
        finally:
            user_sse_connections.pop(user_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
@router.post("/queue/enqueue")
def add_user_to_queue(req: dict):
    enqueue_user(req.domain, req.room_type, req.user_id)
    return {"message": "User added to queue"}


@router.get("/queue/dequeue")
def simulate_room_formation(domain: str, room_type: str):
    users = dequeue_users(domain, room_type, batch_size=1)
    return {"users": users}


@router.get("/queue/length")
def get_queue_size(domain: str, room_type: str):
    length = get_queue_length(domain, room_type)
    return {"queue_length": length}






@router.delete("/room/remove-user")
async def remove_user_from_room(request: Request):
    payload = await request.json()
    user_id = payload.get("user_id")
    room_id = payload.get("room_id")

    result = await db.rooms.rooms_collection.update_one(
        {"room_id": room_id},
        {"$pull": {"users": user_id}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Room or user not found or no change")

    room = await db.rooms.rooms_collection.find_one({"room_id": room_id})
    if room and (not room.get("users") or len(room["users"]) == 0):
        await db.rooms.rooms_collection.delete_one({"room_id": room_id})
        return {
            "message": f"User {user_id} removed, and room {room_id} deleted as it became empty"
        }

    return {
        "message": f"User {user_id} removed from room {room_id}"
    }

# In-memory room and connection storage
rooms = {}  # { room_id: set of WebSockets }
peers = {}  # { WebSocket: peer_id }

@router.websocket("/ws/room/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    peer_id = str(uuid4())
    logging.info(f"New connection: peer_id={peer_id}, room_id={room_id}")

    if room_id not in rooms:
        rooms[room_id] = set()

    # Notify existing peers about new peer and vice versa
    for peer_ws in rooms[room_id]:
        logging.info(f"Notify existing peer {peers[peer_ws]} about new peer {peer_id}")
        await peer_ws.send_json({
            "action": "add-peer",
            "peerID": peer_id,
            "createOffer": False
        })

        logging.info(f"Notify new peer {peer_id} about existing peer {peers[peer_ws]}")
        await websocket.send_json({
            "action": "add-peer",
            "peerID": peers[peer_ws],
            "createOffer": True
        })

    rooms[room_id].add(websocket)
    peers[websocket] = peer_id

    logging.info(f"Sending own peer ID {peer_id} to client")
    await websocket.send_json({
        "action": "assign-peer-id",
        "peerID": peer_id
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            logging.info(f"Received action '{action}' from peer {peer_id}: {message}")

            if action == "relay-sdp":
                target_id = message["peerID"]
                sdp = message["sessionDescription"]
                logging.info(f"Relaying SDP from {peer_id} to {target_id}")
                await send_to_peer(room_id, target_id, {
                    "action": "session-description",
                    "peerID": peer_id,
                    "sessionDescription": sdp
                })

            elif action == "relay-ice":
                target_id = message["peerID"]
                ice = message["iceCandidate"]
                logging.info(f"Relaying ICE candidate from {peer_id} to {target_id}")
                await send_to_peer(room_id, target_id, {
                    "action": "ice-candidate",
                    "peerID": peer_id,
                    "iceCandidate": ice
                })

    except WebSocketDisconnect:
        logging.info(f"Peer {peer_id} disconnected")
        rooms[room_id].remove(websocket)
        del peers[websocket]

        for peer_ws in rooms[room_id]:
            try:
                logging.info(f"Notifying peer {peers[peer_ws]} that {peer_id} left")
                await peer_ws.send_json({
                    "action": "remove-peer",
                    "peerID": peer_id
                })
            except Exception as e:
                logging.error(f"Error notifying peer {peers[peer_ws]}: {e}")

        if not rooms[room_id]:
            del rooms[room_id]
            logging.info(f"Deleted empty room {room_id}")

async def send_to_peer(room_id: str, target_peer_id: str, data: dict):
    for ws in rooms.get(room_id, []):
        if peers.get(ws) == target_peer_id:
            try:
                await ws.send_json(data)
                logging.info(f"Sent data to peer {target_peer_id} in room {room_id}: {data}")
            except Exception as e:
                logging.error(f"Error sending to peer {target_peer_id}: {e}")
            break
