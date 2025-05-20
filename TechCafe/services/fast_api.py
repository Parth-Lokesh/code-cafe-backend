# meet/services/fastapi_api.py
import httpx 
from django.conf import settings

FASTAPI_BASE = settings.FASTAPI_URL  # e.g. http://localhost:9000

def enqueue_user(domain, room_type, user_id):
    url = f"{FASTAPI_BASE}/queue/enqueue"
    payload = {
        "domain": domain,
        "room_type": room_type,
        "user_id": user_id
    }
    with httpx.Client() as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def get_queue_length(domain, room_type):
    url = f"{FASTAPI_BASE}/queue/length"
    params = {"domain": domain, "room_type": room_type}
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def dequeue_users(domain, room_type):
    url = f"{FASTAPI_BASE}/queue/dequeue"
    params = {"domain": domain, "room_type": room_type}
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()
