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
            # Decode the key to string
            decoded_key = key.decode("utf-8")  # Convert bytes to string
            domain, room_type = decoded_key.split(
                ":")[1], decoded_key.split(":")[2]
            length = redis_client.llen(key)

            while length >= ROOM_SIZE:
                users = []
                skipped_users = []

                for _ in range(length):  # loop through all in queue
                    user_data = redis_client.lpop(key)
                    if not user_data:
                        continue

                    user = json.loads(user_data)

                    # Check if user is already in a room
                    if await is_user_already_in_room(user["user_id"]):
                        print(f"Skipping {user['user_id']}: already in a room")
                        continue

                    users.append(user)

                    if len(users) == ROOM_SIZE:
                        break

                # Push skipped users back
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
                    # Requeue unpaired users
                    for user in users:
                        redis_client.rpush(key, json.dumps(user))
                    break  # not enough users to form a room

                length = redis_client.llen(key)

        await asyncio.sleep(2)  # sleep for 2 seconds before checking again
