# fastapi_app/matchmaking/router.py

from fastapi import APIRouter
import asyncio
from fastapi_app.matchmaking.room_creator import matchmaker
from fastapi import APIRouter, HTTPException
from fastapi_app.queue.queue import enqueue_user, dequeue_users, get_queue_length
 
router = APIRouter()

@router.post("/join-queue")
def join_queue(domain: str, user_id: str):
    if not enqueue_user(domain, user_id): 
        raise HTTPException(status_code=400, detail="User already in queue")
    return {"message": f"User {user_id} added to queue for domain {domain}"}

