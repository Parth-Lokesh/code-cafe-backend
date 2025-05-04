import redis
import json

# Connect to Redis (adjust host/port if needed)
redis_client = redis.StrictRedis(
    host='localhost', port=6379, db=0, decode_responses=True)

QUEUE_KEY = "matchmaking_queue"


def enqueue_user(domain: str, room_type: str, user_id: str):
    user_data = json.dumps(
        {"user_id": user_id, "domain": domain, "room_type": room_type})
    redis_client.rpush(QUEUE_KEY, user_data)


def dequeue_users(batch_size=4):
    users = []
    for _ in range(batch_size):
        user_data = redis_client.lpop(QUEUE_KEY)
        if user_data:
            users.append(json.loads(user_data))
    return users


def get_queue_length():
    return redis_client.llen(QUEUE_KEY)
