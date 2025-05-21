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
    peer_id = str(uuid4())
    client = websocket.client

    logging.info(f"🔌 New WebSocket connection attempt from {client} for room {room_id}")

    try:
        await websocket.accept()
        logging.info(f"✅ WebSocket connection accepted for {client}, assigned peer ID: {peer_id}")
    except Exception as e:
        logging.error(f"❌ WebSocket accept failed: {e}")
        logging.error(traceback.format_exc())
        return

    try:
        if room_id not in rooms:
            rooms[room_id] = set()
        rooms[room_id].add(websocket)
        peers[websocket] = peer_id

        logging.info(f"🧩 Peer {peer_id} joined room {room_id} | Total peers: {len(rooms[room_id])}")

        # Send peer their own ID
        await websocket.send_json({
            "action": "assign-peer-id",
            "peerID": peer_id
        })

        # Notify other peers in the room
        for peer_ws in rooms[room_id]:
            if peer_ws == websocket:
                continue

            other_peer_id = peers[peer_ws]

            await peer_ws.send_json({
                "action": "add-peer",
                "peerID": peer_id,
                "createOffer": False
            })

            await websocket.send_json({
                "action": "add-peer",
                "peerID": other_peer_id,
                "createOffer": True
            })

            logging.info(f"🔄 Signaling between new peer {peer_id} and existing peer {other_peer_id}")

        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                action = message.get("action")
                logging.info(f"📩 Received action '{action}' from peer {peer_id}: {message}")

                if action == "relay-sdp":
                    target_id = message["peerID"]
                    sdp = message["sessionDescription"]
                    await send_to_peer(room_id, target_id, {
                        "action": "session-description",
                        "peerID": peer_id,
                        "sessionDescription": sdp
                    })
                    logging.info(f"📡 Relayed SDP from {peer_id} to {target_id}")

                elif action == "relay-ice":
                    target_id = message["peerID"]
                    ice = message["iceCandidate"]
                    await send_to_peer(room_id, target_id, {
                        "action": "ice-candidate",
                        "peerID": peer_id,
                        "iceCandidate": ice
                    })
                    logging.info(f"❄️ Relayed ICE candidate from {peer_id} to {target_id}")

            except Exception as e:
                logging.error(f"❌ Error in message loop for peer {peer_id}: {e}")
                logging.error(traceback.format_exc())
                break

    except WebSocketDisconnect:
        logging.warning(f"⚠️ Peer {peer_id} disconnected from room {room_id}")
    except Exception as e:
        logging.error(f"❌ Unexpected error in WebSocket handler for peer {peer_id}: {e}")
        logging.error(traceback.format_exc())
    finally:
        # Cleanup
        rooms[room_id].remove(websocket)
        peers.pop(websocket, None)

        logging.info(f"🧹 Cleaned up peer {peer_id} from room {room_id}")

        if rooms[room_id]:
            for peer_ws in rooms[room_id]:
                try:
                    await peer_ws.send_json({
                        "action": "remove-peer",
                        "peerID": peer_id
                    })
                    logging.info(f"👋 Notified peer {peers[peer_ws]} about disconnect of {peer_id}")
                except Exception as e:
                    logging.error(f"❌ Failed to notify peer {peers[peer_ws]}: {e}")
        else:
            del rooms[room_id]
            logging.info(f"🚪 Room {room_id} deleted (no remaining peers)")



async def send_to_peer(room_id: str, target_peer_id: str, data: dict):
    for ws in rooms.get(room_id, []):
        if peers.get(ws) == target_peer_id:
            try:
                await ws.send_json(data)
                logging.info(f"📤 Sent to peer {target_peer_id} in room {room_id}: {data}")
                return
            except Exception as e:
                logging.error(f"❌ Error sending to peer {target_peer_id}: {e}")
                logging.error(traceback.format_exc())
                return
    logging.warning(f"⚠️ Target peer {target_peer_id} not found in room {room_id}")