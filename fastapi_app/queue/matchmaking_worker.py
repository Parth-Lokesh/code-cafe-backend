import asyncio
import json
from fastapi_app.database.mongo import db
from fastapi_app.queue.redis_connection import redis_client

ROOM_SIZE = 4


async def is_user_already_in_room(user_id: str) -> bool:
    existing = await db.rooms.find_one({
        "status": "active",
        "users.user_id": user_id
    })
    return existing is not None


async def matchmaking_loop():
    while True:
        keys = redis_client.keys("queue:*")

        for key in keys:
            domain, room_type = key.split(":")[1], key.split(":")[2]
            length = redis_client.llen(key)

            while length >= ROOM_SIZE:
                users = []
                skipped_users = []

                for _ in range(length):
                    user_data = redis_client.lpop(key)
                    if not user_data:
                        continue

                    user = json.loads(user_data)

                    if await is_user_already_in_room(user["user_id"]):
                        print(f"Skipping {user['user_id']}: already in a room")
                        skipped_users.append(user)
                        continue

                    users.append(user)
                    if len(users) == ROOM_SIZE:
                        break

                # Re-queue skipped users
                for user in skipped_users:
                    redis_client.rpush(key, json.dumps(user))

                if len(users) == ROOM_SIZE:
                    room = {
                        "domain": domain,
                        "room_type": room_type,
                        "users": users,
                        "status": "active"
                    }
                    await db.rooms.insert_one(room)
                    print(f"Room created: {room}")
                else:
                    # Requeue the unmatched users
                    for user in users:
                        redis_client.rpush(key, json.dumps(user))
                    break  # Not enough valid users

                length = redis_client.llen(key)

        await asyncio.sleep(2)
