# fastapi_app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_app.code_editor.router import router as editor_router  # ✅ this line

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(editor_router)  # ✅ register the router

@app.get("/")
def root():
    return {"msg": "Backend running"}
