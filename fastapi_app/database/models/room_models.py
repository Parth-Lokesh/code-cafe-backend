from pydantic import BaseModel
from typing import List


class Room(BaseModel):
    domain: str
    room_type: str
    participants: List[str]  # List of user_ids
