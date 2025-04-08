from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from Routes.conversation import router as conversation_router
import os
import uvicorn

app = FastAPI()

# Correct usage of add_middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
os.makedirs("video_uploads", exist_ok=True)

# Mount the directory as a static files directory
app.mount("/video_uploads", StaticFiles(directory="video_uploads"), name="video_uploads")
app.include_router(conversation_router, prefix="/interview", tags=["conversation"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True)
