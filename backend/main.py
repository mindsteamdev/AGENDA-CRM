from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load env before importing services that rely on env vars
load_dotenv(dotenv_path="backend/.env")

from backend.services.chatbot import chatbot_router
from backend.services.booking import booking_router
from backend.services.data import data_router
from backend.services.tts import tts_router
from backend.services.vapi import vapi_router

app = FastAPI(title="Restaurant Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router, prefix="/api/chat", tags=["Chatbot"])
app.include_router(booking_router, prefix="/api/booking", tags=["Booking"])
app.include_router(data_router, prefix="/api/data", tags=["Data"])
app.include_router(tts_router, prefix="/api/tts", tags=["TTS"])
app.include_router(vapi_router, prefix="/api/vapi", tags=["Vapi"])

@app.get("/")
async def root():
    return {"message": "Restaurant Chatbot API is running"}
