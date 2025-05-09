from fastapi import APIRouter, HTTPException
from google import genai
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import os
import random
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi_app.database.mongo import db
import re
from pydantic import BaseModel
from typing import List, Dict
from fastapi_app.questiongenerator.prompts import coding_prompt,debugging_prompt


# Load env variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

router = APIRouter()

# MongoDB
rooms_collection = db.rooms

async def generate_prompt_response(prompt):
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=[prompt])
    return response.text


def extract_json_block(text):
    match = re.search(r'{.*}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    else:
        raise ValueError("No valid JSON found in Gemini response.")

@router.post("/generate_questions/{room_id}")
async def generate_questions(room_id: str):
    try:
        room = await rooms_collection.find_one({"room_id": room_id})
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        questions = []
        q_type = room["room_type"]

        for _ in range(3):
            if q_type == "coding":
                q_data_str = await generate_prompt_response(coding_prompt)
            else:
                q_data_str = await generate_prompt_response(debugging_prompt)

            q_data = extract_json_block(q_data_str)

            # Add question type
            q_data["type"] = q_type

            if q_type == "coding":
                required_fields = ["question", "test_cases", "output_datatype", "boilerplate_code_user", "boilerplate_code_main"]
                missing_fields = [field for field in required_fields if field not in q_data]

                if missing_fields:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Incomplete coding question data. Missing fields: {missing_fields}"
                    )

            questions.append(q_data)

        await rooms_collection.update_one(
            {"room_id": room_id},
            {"$set": {"questions": questions}}
        )

        return {"message": "Questions generated successfully", "questions": questions}

    except HTTPException as e:
        raise e  # re-raise custom errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms")
async def get_all_rooms():
    try:
        rooms = await rooms_collection.find().to_list(length=None)
        for room in rooms:
            room["_id"] = str(room["_id"]) 
        return rooms
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/get-questions/{user_id}")
async def get_questions_by_user(user_id: str):
    room = await rooms_collection.find_one({
        "users": {"$elemMatch": {"user_id": user_id}}
    })

    if not room:
        raise HTTPException(
            status_code=404, detail="User not found in any room.")

    questions = room.get("questions")
    if not questions:
        raise HTTPException(
            status_code=404, detail="No questions found in the room.")

    return JSONResponse(content={"questions": questions})
