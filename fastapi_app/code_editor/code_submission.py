import httpx
from bson import ObjectId
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi_app.database.mongo import db
import requests
# from fastapi.middleware.cors import CORSMiddleware
import os

router = APIRouter()

questions_collection = db.rooms 

# Piston API URL
PISTON_API_URL = "https://api.piston.com/execute"


class SubmitCodeRequest(BaseModel):
    user_id: str
    question_id: int
    code: str
    language: Literal["python", "java", "c++"]


router = APIRouter()
questions_collection = db.rooms


@router.post("/submit-code")
async def submit_code(payload: SubmitCodeRequest):
    print("Looking for user_id:", payload.user_id)
    document = await questions_collection.find_one({"users.user_id": payload.user_id})

    if not document:
        raise HTTPException(
            status_code=404, detail=f"No document found for user_id '{payload.user_id}'.")

    try:
        question = document["questions"][payload.question_id]
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid question index.")

    boilerplate_main = question["boilerplate_code_main"][payload.language]
    print(boilerplate_main)

    if payload.language == "java":
        full_code = boilerplate_main + "\n\n" + payload.code
    else:
        full_code = payload.code + "\n\n" + boilerplate_main

    # Fetch latest version for the selected language
    async with httpx.AsyncClient() as client:
        runtimes_response = await client.get("https://emkc.org/api/v2/piston/runtimes")
        runtimes = runtimes_response.json()

    matching_runtimes = [r for r in runtimes if r["language"] == payload.language]
    if not matching_runtimes:
        raise HTTPException(status_code=400, detail=f"No runtime found for language: {payload.language}")

    latest_version = matching_runtimes[-1]["version"]

    compile_payload = {
        "language": payload.language,
        "version": latest_version,
        "files": [{"content": full_code}]
    }

    print("Sending code to /run-code endpoint...")

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/run-code", json=compile_payload)
        result = response.json()
        output = result.get("run", {}).get("output", "").strip()
        print(result)
        print(output)
        if output == "true":
            return {"result": "All test cases passed."}
        elif output.startswith("false-"):
            failed_case = output.split("-")[1]
            return {"result": f"Hidden test case failed at case #{failed_case}."}
        else:
            return {"result": "Unexpected output format", "raw_output": output}

    

