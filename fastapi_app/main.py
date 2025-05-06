# fastapi_app/main.py

from fastapi_app.questiongenerator.questions import router as questions_router
from fastapi_app.queue.matchmaking_worker import matchmaking_loop
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_app.code_editor.router import router as editor_router
from fastapi_app.domain.router import router as domain_router
from fastapi_app.matchmaking.router import router as matchmaking_router
from fastapi_app.queue.router import router as queue_router
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from fastapi_app.queue.matchmaking_worker import matchmaking_loop
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start matchmaking task
    asyncio.create_task(matchmaking_loop())
    yield  # App runs here
    # (Optional) Add shutdown logic after this if needed

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

# Register routers
app.include_router(editor_router)
app.include_router(domain_router, prefix="/api")
app.include_router(matchmaking_router, prefix="/api/matchmaking")
app.include_router(queue_router, prefix="/api")
app.include_router(questions_router, prefix="/api/questions")


@app.get("/")
def root():
    return {"msg": "Backend running"}


@app.post("/run-code")
async def run_code(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(PISTON_URL, json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
