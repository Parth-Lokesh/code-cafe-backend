from fastapi import APIRouter, HTTPException
from fastapi_app.database.mongo import db
from fastapi_app.database.models.domain_models import Domain, RoomType
from bson import ObjectId

router = APIRouter()


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("/domain")
async def create_domain(domain: Domain):
    existing = await db.domains.find_one({"name": domain.name})
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists.")
    await db.domains.insert_one(domain.dict())
    return {"message": "Domain created"}


@router.get("/domain")
async def list_domains():
    domains = await db.domains.find().to_list(100)
    return [serialize_doc(doc) for doc in domains]


@router.post("/room-type")
async def create_room_type(rt: RoomType):
    await db.room_types.insert_one(rt.dict())
    return {"message": "Room type created"}


@router.get("/room-type")
async def list_room_types():
    room_types = await db.room_types.find().to_list(100)
    return [serialize_doc(doc) for doc in room_types]


@router.get("/get-room/{user_id}")
async def get_room(user_id: str):
    room = await db.rooms.find_one({
        "status": "active",
        "users.user_id": user_id
    })

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return {"room_id": room["room_id"]}
