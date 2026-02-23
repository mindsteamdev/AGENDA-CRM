from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import time
import os
import google.generativeai as genai
from .nocodb import nocodb_service

vapi_router = APIRouter()

# Intentamos inicializar Gemini si hay API key
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@vapi_router.post("/chat/completions")
async def vapi_chat_completions(request: Request):
    """
    Endpoint compatible con OpenAI que Vapi usa como "Custom LLM".
    Recibe el historial (messages) de Vapi, lo adapta para Gemini,
    consulta NocoDB si encontramos información relevante,
    y devuelve la respuesta de Gemini como un flujo SSE.
    """
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    try:
        body = await request.json()
        print(f"DEBUG VAPI: Received request")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages = body.get("messages", [])
    
    # Extraer el objeto call si Vapi lo envía
    call_data = body.get("call", {})
    customer_phone = None
    if call_data and 'customer' in call_data and 'number' in call_data['customer']:
        customer_phone = call_data['customer']['number']

    contents = []
    system_instruction = None
    
    # Convertir el formato OpenAI a Gemini
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        
        if role == "system":
            system_instruction = content
        elif role == "user":
            contents.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [content]})
            
    # Lógica VIP basada en el número de teléfono (si logramos tenerlo)
    loyalty_info = ""
    if customer_phone:
        try:
            loyalty = nocodb_service.get_customer_loyalty(customer_phone)
            if loyalty and loyalty.get("loyalty_tier") == "VIP":
                loyalty_info = f"[INFO INTERNA: El cliente es {loyalty.get('customer_name')}, categoría VIP]"
        except Exception as e:
            print(f"Error consulting NocoDB for Vapi caller: {e}")
            
    # Alternativa: Si no hay teléfono pero sí mencionan nombre en los mensajes
    # (El agente Vapi le podría preguntar su nombre).
    # Por ahora inyectamos loyalty_info en el último mensaje del usuario si existe.
    if loyalty_info and contents and contents[-1]["role"] == "user":
        last_text = contents[-1]["parts"][0]
        contents[-1]["parts"][0] = f"{loyalty_info} {last_text}"

    # Instanciar el modelo
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_instruction
    )
    
    try:
        # Habilitar stream=True para entregar voz de baja latencia a Vapi
        response_stream = model.generate_content(contents, stream=True)
    except Exception as e:
        print(f"Error calling Gemini from Vapi: {e}")
        raise HTTPException(status_code=500, detail="Error generating content")

    async def generate_sse():
        """Generador para devolver la respuesta en formato Server-Sent Events (SSE) compatible con OpenAI"""
        chunk_id = f"chatcmpl-{int(time.time())}"
        
        for chunk in response_stream:
            # text property puede dar error si chunk fue bloqueado por seguridad
            try:
                text = chunk.text
            except Exception:
                continue
                
            if text:
                sse_data = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "vapi-custom-gemini",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(sse_data)}\n\n"
        
        # Último chunk indicando el fin
        final_data = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "vapi-custom-gemini",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate_sse(), media_type="text/event-stream")
