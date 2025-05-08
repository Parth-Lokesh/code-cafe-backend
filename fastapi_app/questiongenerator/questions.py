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

    Include:
    1. Only 2 sample test cases (used for visible testing), in this format:
    Input: <input>
    Expected Output: <output>

    2. The output datatype (one of: "int", "str", "float", "bool", "list[int]", "list[str]", etc).

    3. Boilerplate code for three languages (Python, Java, C++).
    Each should include:
        - A function/class definition named appropriately where user writes code.
        - A main function that runs all 10 hardcoded test cases, hardcode those test cases and expected answers in two arrays and then in a loop perform validation 
        - Assume the user only writes the core function logic in the function/class definition.
        - Do not give the logic of the solution anywhere, neither in the user's boilerplate nor in the main boilerplate, provide only function/class definition. 
        - For java, import the required libraries in boilerplate Main class code, and not in Solution class.

    In the main function logic store inputs and outputs for test cases in arrays and then check, and after checking each test case:
    - If all tests pass, print "true"
    - If any test fails, immediately print "false-<i>", where i is the failing test case index (1-based), and stop further checks.

    Respond strictly in JSON like:
    {
    "question": "...",
    "test_cases": [
        { "input": "5", "output": "True" },
        { "input": "4", "output": "False" }
    ],
    "output_datatype": "bool",
    "boilerplate_code_user": {
        "python": "def solve(...):\\n    # your code here",
        "java": "public class Solution {\\n    // your code here\\n}",
        "c++": "#include <iostream>\\nusing namespace std;\\n\\nvoid solve() {\\n    // your code here\\n}"
    },
    "boilerplate_code_main": {
        "python": "if __name__ == '__main__':\\n    # call solve() with input/output logic",
        "java": "public class Main {\\n    public static void main(String[] args) {\\n        // call Solution logic\\n    }\\n}",
        "c++": "int main() {\\n    // call solve();\\n    return 0;\\n}"
    }
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
                q_data_str = await generate_coding_question()
            else:
                q_data_str = await generate_debugging_question()

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
