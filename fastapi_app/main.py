# fastapi_app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_app.code_editor.router import router as editor_router
from fastapi_app.domain.router import router as domain_router
from fastapi_app.matchmaking.router import router as matchmaking_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(editor_router)
app.include_router(domain_router, prefix="/api")
app.include_router(matchmaking_router, prefix="/api/matchmaking")


@app.get("/")
def root():
    return {"msg": "Backend running"}
