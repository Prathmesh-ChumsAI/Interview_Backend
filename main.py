from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.conversation import router as conversation_router
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

app.include_router(conversation_router, prefix="/interview", tags=["conversation"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True)
