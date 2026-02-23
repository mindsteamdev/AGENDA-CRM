from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

tts_router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@tts_router.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    
    # Voice selection strategy for 'SaborIA':
    # Priority: es-US-Neural2-A (Female) since es-CL is unavailable in current project tier.
    
    voice_name = "es-US-Neural2-A" 
    language_code = "es-US"

    payload = {
        "input": {
            "text": request.text
        },
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
            "ssmlGender": "FEMALE"
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "pitch": 0.5, # Slightly higher pitch for a more 'concierge' feel
            "speakingRate": 0.95 # Slightly slower for better articulation
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            # Fallback 1: US Standard Spanish (In case Neural is unavailable)
            print(f"DEBUG: Neural failed ({response.status_code}), trying US Standard...")
            payload["voice"]["languageCode"] = "es-US"
            payload["voice"]["name"] = "es-US-Standard-A"
            response = requests.post(url, json=payload)

        if response.status_code != 200:
            print(f"DEBUG: TTS API Error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Google Cloud TTS API Error: {response.text}")
        
        data = response.json()
        audio_content = data.get("audioContent")
        
        if not audio_content:
            raise HTTPException(status_code=500, detail="No audio content returned from Google Cloud TTS")
            
        return {"audioContent": audio_content}

    except Exception as e:
        print(f"DEBUG: Unexpected Error in TTS synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
