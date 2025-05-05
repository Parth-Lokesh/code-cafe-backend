# fastapi_app/matchmaking/router.py

from fastapi import APIRouter
import asyncio
from fastapi_app.matchmaking.room_creator import matchmaker
from fastapi import APIRouter, HTTPException
from fastapi_app.redis.queue import enqueue_user, dequeue_users, get_queue_length
 
router = APIRouter()

## Force Add
@router.post("/enqueue")
def enqueue(domain: str, room_type: str, user_id: str):
    enqueue_user(domain, room_type, user_id)
    return {"message": "User added to queue", "queue_length": get_queue_length()}

## Force Remove
@router.get("/dequeue")
def dequeue():
    users = dequeue_users()
    if len(users) == 4:
        return {"message": "Room formed", "users": users}
    return {"message": "Not enough users yet", "users": users}


@router.post("/join-queue")
def join_queue(domain: str, room_type: str, user_id: str):
    if not enqueue_user(domain, room_type, user_id):
        raise HTTPException(status_code=400, detail="User already in queue")
    return {"message": f"User {user_id} added to queue"}


@router.post("/start-matching")
async def start_matching(domain: str, room_type: str):
    asyncio.create_task(matchmaker(domain, room_type))
    return {"message": f"Started matchmaking for {domain} - {room_type}"}
