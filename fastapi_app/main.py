from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Optional
import asyncio
import httpx
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
# Load environment variables
load_dotenv()

# --- Configuration ---
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 20160))
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://code-cafe-frontend.netlify.app")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
PISTON_URL = "https://emkc.org/api/v2/piston/execute"

# --- Lifespan ---
from fastapi_app.queue.matchmaking_worker import matchmaking_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(matchmaking_loop())
    yield

# --- App Initialization ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://code-cafe-frontend.netlify.app"],  # Your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- Pydantic Models ---
class TokenData(BaseModel):
    username: Optional[str] = None
    github_id: Optional[str] = None

class User(BaseModel):
    username: str
    github_id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None

# --- JWT Helpers ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request) -> Optional[User]:
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return User(
            username=payload.get("sub"),
            github_id=payload.get("github_id"),
            name=payload.get("name"),
            avatar_url=payload.get("avatar_url")
        )
    except JWTError:
        return None

# --- Routers ---
from fastapi_app.questiongenerator.questions import router as questions_router
from fastapi_app.code_editor.router import router as editor_router
from fastapi_app.domain.router import router as domain_router
from fastapi_app.matchmaking.router import router as matchmaking_router
from fastapi_app.queue.router import router as queue_router
from fastapi_app.code_editor.code_submission import router as code_submission_router

app.include_router(editor_router)
app.include_router(domain_router, prefix="/api")
app.include_router(matchmaking_router, prefix="/api/matchmaking")
app.include_router(queue_router, prefix="/api")
app.include_router(questions_router, prefix="/api/questions")
app.include_router(code_submission_router, prefix="/api/questions")

# --- Basic Routes ---
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

# --- GitHub OAuth ---
@app.get("/auth/github/login")
async def github_login():
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=user:email,read:user"
    )
    return RedirectResponse(github_auth_url)
@app.get("/test-cors")
def test_cors():
    return {"message": "CORS is working"}

@app.post("/api/auth/github/token")
async def exchange_github_code_for_token(payload: dict):
    code=payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, json=payload, headers=headers)
        token_data = token_response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub access token not received")

        user_headers = {"Authorization": f"token {access_token}"}
        user_response = await client.get("https://api.github.com/user", headers=user_headers)
        user_data = user_response.json()
        print(user_data)
    github_login = user_data.get("login")
    github_id = str(user_data.get("id"))
    session_data = {
        "sub": github_login,
        "github_id": github_id,
        "name": user_data.get("name"),
        "avatar_url": user_data.get("avatar_url")
    }

    session_token = create_access_token(data=session_data)

    response = JSONResponse(content={
        "message": "Successfully authenticated with GitHub!",
        "user": session_data,
        "access_token": session_token
    })
    secure_cookie = os.getenv("COOKIE_SECURED", "false").lower() == "true"
    response.set_cookie(
    key="session_token",
    value=session_token,
    httponly=True,
    samesite="lax",  # or "None" if you're doing cross-site cookies
    secure=secure_cookie,  # ✅ Required for HTTPS
    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    expires=datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


    return response

# --- Protected Route ---
@app.get("/api/users/me", response_model=Optional[User])
async def read_users_me(current_user: Optional[User] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Token expired or not authenticated. Please log in again.")
    return current_user

# --- Logout ---
@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse(content={"message": "Successfully logged out"})
    response.delete_cookie("session_token", httponly=True, samesite="lax", secure=True)
    return response


rooms: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = []

    for peer in rooms[room_id]:
        await peer.send_json({
            "action": "add-peer",
            "peerID": id(websocket),
            "createOffer": True
        })
        await websocket.send_json({
            "action": "add-peer",
            "peerID": id(peer),
            "createOffer": False
        })

    rooms[room_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            peer_id = data.get("peerID")

            for peer in rooms[room_id]:
                if id(peer) == peer_id:
                    await peer.send_json({
                        "action": action,
                        "peerID": id(websocket),
                        **{k: v for k, v in data.items() if k != "action" and k != "peerID"}
                    })
                    break

    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        for peer in rooms[room_id]:
            await peer.send_json({
                "action": "remove-peer",
                "peerID": id(websocket)
            })
# # fastapi_app/main.py

# from fastapi_app.questiongenerator.questions import router as questions_router
# from fastapi_app.queue.matchmaking_worker import matchmaking_loop
# import asyncio
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from fastapi_app.code_editor.router import router as editor_router
# from fastapi_app.domain.router import router as domain_router
# from fastapi_app.matchmaking.router import router as matchmaking_router
# from fastapi_app.queue.router import router as queue_router
# from fastapi_app.code_editor.code_submission import router as code_submission_router
# from fastapi import FastAPI
# from contextlib import asynccontextmanager
# import asyncio
# from fastapi_app.queue.matchmaking_worker import matchmaking_loop
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# import httpx

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Start matchmaking task
#     asyncio.create_task(matchmaking_loop())
#     yield  # App runs here
#     # (Optional) Add shutdown logic after this if needed

# app = FastAPI(lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# PISTON_URL = "https://emkc.org/api/v2/piston/execute"

# # Register routers
# app.include_router(editor_router)
# app.include_router(domain_router, prefix="/api")
# app.include_router(matchmaking_router, prefix="/api/matchmaking")
# app.include_router(queue_router, prefix="/api")
# app.include_router(questions_router, prefix="/api/questions")
# app.include_router(code_submission_router, prefix="/api/questions")


# @app.get("/")
# def root():
#     return {"msg": "Backend running"}


# @app.post("/run-code")
# async def run_code(request: Request):
#     payload = await request.json()
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(PISTON_URL, json=payload)
#             return response.json()
#         except Exception as e:
#             return {"error": str(e)}


