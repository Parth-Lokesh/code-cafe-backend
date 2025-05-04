# fastapi_app/matchmaking/router.py

from fastapi import APIRouter
from fastapi_app.redis.queue import enqueue_user, dequeue_users, get_queue_length

router = APIRouter()


@router.post("/enqueue")
def enqueue(domain: str, room_type: str, user_id: str):
    enqueue_user(domain, room_type, user_id)
    return {"message": "User added to queue", "queue_length": get_queue_length()}


@router.get("/dequeue")
def dequeue():
    users = dequeue_users()
    if len(users) == 4:
        return {"message": "Room formed", "users": users}
    return {"message": "Not enough users yet", "users": users}
