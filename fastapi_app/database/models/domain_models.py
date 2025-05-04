from pydantic import BaseModel

class Domain(BaseModel):
    name: str
    description: str


class RoomType(BaseModel):
    name: str
    domain_name: str
