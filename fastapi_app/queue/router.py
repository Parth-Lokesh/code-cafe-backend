from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi_app.redis.queue import enqueue_user, dequeue_users, get_queue_length

router = APIRouter()


class QueueRequest(BaseModel):
    domain: str
    room_type: str
    user_id: str


@router.post("/queue/enqueue")
def add_user_to_queue(req: QueueRequest):
    enqueue_user(req.domain, req.room_type, req.user_id)
    return {"message": "User added to queue"}


@router.get("/queue/dequeue")
def simulate_room_formation(domain: str, room_type: str):
    users = dequeue_users(domain, room_type, batch_size=4)
    return {"users": users}


@router.get("/queue/length")
def get_queue_size(domain: str, room_type: str):
    length = get_queue_length(domain, room_type)
    return {"queue_length": length}

