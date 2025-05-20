import httpx
from bson import ObjectId
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi_app.database.mongo import db
import requests
from datetime import datetime

# from fastapi.middleware.cors import CORSMiddleware
import os

# Piston API URL
PISTON_API_URL = "https://api.piston.com/execute"


class SubmitCodeRequest(BaseModel):
    user_id: str
    room_id: str
    question_id: int  
    code: str
    language: Literal["python", "java", "c++"]

router = APIRouter()
questions_collection = db.rooms

@router.post("/submit-code")
async def submit_code(payload: SubmitCodeRequest):
    # 🔍 Get the room document containing this user
    document = await questions_collection.find_one({"users.user_id": payload.user_id})
    if not document:
        raise HTTPException(status_code=404, detail="User data not found.")

    # 🎯 Fetch the correct question based on question_id (0,1,2)
    try:
        question = document["questions"][int(payload.question_id)]
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid question index.")

    # 🔧 Merge user code with backend-only main boilerplate
    boilerplate_main = question["boilerplate_code_main"].get(payload.language)
    if not boilerplate_main:
        raise HTTPException(status_code=400, detail="Language not supported.")

    full_code = (
        boilerplate_main + "\n\n" + payload.code
        if payload.language == "java"
        else payload.code + "\n\n" + boilerplate_main
    )

    # 🛠 Get latest runtime version for the language
    async with httpx.AsyncClient() as client:
        runtimes_response = await client.get("https://emkc.org/api/v2/piston/runtimes")
        runtimes = runtimes_response.json()

    matching_runtimes = [
        r for r in runtimes if r["language"] == payload.language]
    if not matching_runtimes:
        raise HTTPException(status_code=400, detail="No runtime found.")
    latest_version = matching_runtimes[-1]["version"]

    # 🚀 Compile code via local runner
    compile_payload = {
        "language": payload.language,
        "version": latest_version,
        "files": [{"content": full_code}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/run-code", json=compile_payload)
        result = response.json()
        output = result.get("run", {}).get("output", "").strip()

    # ✅ Success case
    if output == "true":
        await questions_collection.update_one(
            {"room_id": payload.room_id, "users.user_id": payload.user_id},
            {"$addToSet": {"users.$.questions_solved": payload.question_id}}
        )

        # 🔄 Recheck if user finished all 3 questions
        updated_room = await questions_collection.find_one({"room_id": payload.room_id})
        user_entry = next(
            (u for u in updated_room["users"] if u["user_id"] == payload.user_id), None)

        if user_entry and len(user_entry.get("questions_solved", [])) == 3:
            await questions_collection.update_one(
                {"room_id": payload.room_id},
                {
                    "$set": {
                        "challenge_status": "ended",
                        "winner_id": payload.user_id,
                        "ended_at": datetime.utcnow()
                    }
                }
            )
            return {
                "all_test_cases_passed": True,
                "result": "✅ You solved all 3 questions!",
                "challenge_over": True,
                "popup": {
                    "message": "Challenge over!",
                    "winner_id": payload.user_id,
                    "options": ["Shuffle", "Exit Room"]
                }
            }

        return {"result": "✅ Question passed!", "challenge_over": False}

    # ❌ Failed hidden test case
    elif output.startswith("false-"):
        failed_case = output.split("-")[1]
        return {"result": f"❌ Hidden test case failed at case #{failed_case}."}

    # ❌ Unknown compiler output
    return {"result": "❌ Unexpected output format"}
