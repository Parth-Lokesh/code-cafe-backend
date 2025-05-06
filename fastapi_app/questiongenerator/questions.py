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

# Load env variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") 

client = genai.Client(api_key=api_key)

router = APIRouter()

# MongoDB
rooms_collection = db.rooms


@router.get("/test-gemini")
async def test_gemini():
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="How does AI work?"
        )
        return {"response": response.text}
    except Exception as e:
        return {"error": str(e)}

async def generate_coding_question():
    prompt = """
    Generate a simple to medium difficulty coding question.
    Also generate 10 test cases in this format:
    Input: <input>
    Expected Output: <output>

    Respond strictly in JSON like:
    {
        "question": "...",
        "test_cases": [
            {"input": "5", "output": "True"},
            ...
        ]
    }
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=[prompt])
    return response.text


async def generate_debugging_question():
    prompt = """
    Generate a buggy Python code snippet and a brief problem statement.
    Provide 10 test cases with correct outputs.

    Respond strictly in JSON like:
    {
        "question": "...",
        "buggy_code": "...",
        "test_cases": [
            {"input": "5", "output": "120"},
            ...
        ]
    }
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
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
        # Use custom room_id string
        room = await rooms_collection.find_one({"room_id": room_id})
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        questions = []
        q_type = room["room_type"]
        for _ in range(3):
            if q_type == "coding":
                q_data_str = await generate_coding_question()
            else:
                q_data_str = await generate_debugging_question()
        
            q_data = extract_json_block(q_data_str)
            q_data["type"] = q_type
            questions.append(q_data)

        await rooms_collection.update_one(
            {"room_id": room_id},
            {"$set": {"questions": questions}}
        )

        return {"message": "Questions generated successfully", "questions": questions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms")
async def get_all_rooms():
    try:
        rooms = await rooms_collection.find().to_list(length=None)
        for room in rooms:
            room["_id"] = str(room["_id"])  # convert ObjectId to string
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
