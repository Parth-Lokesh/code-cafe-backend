import redis
import json
from fastapi_app.queue.redis_connection import redis_client

def get_queue_key(domain: str, room_type: str) -> str:
    return f"queue:{domain}:{room_type}"


def is_user_already_in_queue(domain: str, room_type: str, user_id: str) -> bool:
    queue_key = get_queue_key(domain, room_type)
    queue = redis_client.lrange(queue_key, 0, -1)
    for item in queue:
        data = json.loads(item)
        if data["user_id"] == user_id:
            return True
    return False


def enqueue_user(domain: str, user_id: str) -> bool:
    queue_key = f"queue:{domain}"

    existing_users = redis_client.lrange(queue_key, 0, -1)
    for u in existing_users:
        user = json.loads(u)
        if user["user_id"] == user_id:
            return False  # already in queue

    user_data = {"user_id": user_id}
    redis_client.rpush(queue_key, json.dumps(user_data))
    return True


def dequeue_users(domain: str, room_type: str, batch_size=1):
    queue_key = get_queue_key(domain, room_type)
    users = []
    for _ in range(batch_size):
        user_data = redis_client.lpop(queue_key)
        if user_data:
            users.append(json.loads(user_data))
    return users


def get_queue_length(domain: str, room_type: str):
    queue_key = get_queue_key(domain, room_type)
    return redis_client.llen(queue_key)
