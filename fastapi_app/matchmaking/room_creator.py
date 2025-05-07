import json
import time
import asyncio
from fastapi_app.database.mongo import db
from fastapi_app.redis.queue import dequeue_users, get_queue_key, redis_client


async def matchmaker(domain: str, room_type: str):
    queue_key = get_queue_key(domain, room_type)
    while True:
        queue_length = redis_client.llen(queue_key)
        if queue_length >= 4:
            users = dequeue_users(domain, room_type, 4)
            user_ids = [u["user_id"] for u in users]
            await db.rooms.insert_one({
                "domain": domain,
                "room_type": room_type,
                "participants": user_ids
            })
            print(
                f"✅ Room created for {domain} - {room_type} with users: {user_ids}")
        await asyncio.sleep(2)  # Check every 2 seconds
