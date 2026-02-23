from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from .nocodb import nocodb_service

chatbot_router = APIRouter()

# Initialize Gemini AI with API Key
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        
        def registrar_reserva(nombre: str, cantidad: int, fecha_hora: str, telefono: str) -> str:
            """
            Registra una nueva reserva de mesas en el restaurante dentro de la base de datos (NocoDB).
            Úsala SIEMPRE que el usuario confirme explícitamente que quiere hacer una reserva y te haya proporcionado
            los 4 datos requeridos.
            
            Args:
                nombre: El nombre completo del cliente.
                cantidad: El número de personas que asistirán (ej. 2).
                fecha_hora: La fecha y hora de la reserva en formato ISO 8601 (ej. '2023-12-31T20:00:00').
                telefono: El número de contacto del cliente.
            
            Returns:
                Un mensaje de texto confirmando si la reserva fue exitosa o si hubo un error de disponibilidad.
            """
            import uuid
            
            # Gemini a veces manda floats como 2.0 en lugar de ints
            cantidad_int = int(cantidad)
            
            print(f"DEBUG TOOL: Intentando registrar reserva para {nombre} ({cantidad_int} personas) el {fecha_hora}")
            # 1. Verificar disponibilidad (reutilizando lógica existente)
            is_available = nocodb_service.check_resource_availability(cantidad_int, fecha_hora)
            if not is_available:
                print("DEBUG TOOL: No hay disponibilidad.")
                return "Error: No hay mesas disponibles para esa cantidad de personas a esa hora."
                
            # 2. Sincronizar con NocoDB
            booking_id = str(uuid.uuid4())
            booking_sync_data = {
                "booking_id": booking_id,
                "customer_name": nombre,
                "customer_phone": telefono,
                "booking_time": fecha_hora,
                "party_size": cantidad_int
            }
            
            success = nocodb_service.sync_booking(booking_sync_data)
            if success:
                print(f"DEBUG TOOL: NocoDB reportó éxito para {nombre}")
                
                # 3. Guardar cliente si es nuevo
                try:
                    nocodb_service.create_customer_if_not_exists(telefono, nombre)
                except Exception as e:
                    print(f"DEBUG TOOL: Fallo guardando cliente {nombre}: {e}")
                    
                return f"Éxito: Reserva confirmada con ID {booking_id[:8]}."
            else:
                print(f"DEBUG TOOL: NocoDB reportó FALLO al sincronizar {nombre}")
                return "Error: Problema de conexión con la base de datos al guardar."

        def agregar_lista_espera(nombre: str, cantidad: int, fecha_hora: str, telefono: str) -> str:
            """
            Agrega a un cliente a la lista de espera cuando no hay mesas disponibles para registrar_reserva.
            Úsala SIEMPRE que el cliente confirme explícitamente que desea unirse a la lista de espera para ese horario.
            
            Args:
                nombre: El nombre completo del cliente.
                cantidad: El número de personas que asistirán (ej. 2).
                fecha_hora: La fecha y hora de la reserva deseada en formato ISO 8601.
                telefono: El número de contacto del cliente.
            
            Returns:
                Un mensaje de texto confirmando si se agregó a la lista de espera exitosamente.
            """
            cantidad_int = int(cantidad)
            print(f"DEBUG TOOL: Intentando agregar a lista de espera a {nombre} ({cantidad_int} personas) el {fecha_hora}")
            
            waitlist_data = {
                "customer_name": nombre,
                "customer_phone": telefono,
                "booking_time": fecha_hora,
                "party_size": cantidad_int
            }
            
            success = nocodb_service.add_to_waitlist(waitlist_data)
            if success:
                print(f"DEBUG TOOL: NocoDB reportó éxito para lista de espera de {nombre}")
                try:
                    nocodb_service.create_customer_if_not_exists(telefono, nombre)
                except Exception as e:
                    pass
                return "Éxito: Cliente agregado a la lista de espera."
            else:
                print(f"DEBUG TOOL: NocoDB reportó FALLO al agregar lista de espera {nombre}")
                return "Error: Problema de conexión al guardar en lista de espera."

        # Define the persona and context
        system_instruction = \"\"\"
        Eres 'SaborIA', la concierge digital del restaurante 'Sabor Divino' en Santiago, Chile.
        
        Tu personalidad:
        - Eres sofisticada pero cercana. Como una buena anfitriona chilena.
        - Hablas de forma natural, usando chilenismos sutiles como 'po', 'claro que sí', '¿le parece?'.
        - Escribe en minúsculas la mayoría del tiempo para mantener una vibra de chat relajada.
        - Tu tono es elegante, cálido y profesional. No eres un robot, eres parte del alma del restaurante.
        
        Sobre el restaurante:
        - 'Sabor Divino' ofrece una fusión única entre el Mediterráneo y los sabores locales de Chile.
        - Platos icónicos: 'Risotto de Cordero Magallánico' ($24.000), 'Ceviche de Reineta al estilo Sabor' ($19.000).
        - Ubicación: Barrio Lastarria (Sector exclusivo de Santiago).
        - Horario: Martes a Sábado (13:00 a 23:00), Domingo (13:00 a 17:00).
        
        Tu misión:
        1. Encantar a los clientes con recomendaciones personalizadas.
        2. Gestionar reservas. Si un cliente quiere reservar, PIDE LOS 4 DATOS (nombre, cantidad de personas, fecha/hora y teléfono) de forma amable y conversacional ANTES de usar tu herramienta de registro.
        3. Si intentas usar `registrar_reserva` y te devuelve 'Error: No hay mesas', diles cordialmente que se ha llenado el aforo y pregúntales directamente si desean anotarse en la Lista de Espera para esa hora.
        4. Si te dicen que sí, usa tu herramienta `agregar_lista_espera` con sus datos para anotarlos.
        5. Si el cliente menciona su nombre o teléfono en la charla, podrías notar que son recurrentes (VIP).
        
        Reglas de formato:
        - Respuestas breves (máximo 3 frases).
        - Máximo un emoji por mensaje.
        - Omite signos de interrogación al inicio (estilo chat moderno).
        \"\"\"
        
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=system_instruction,
            tools=[registrar_reserva, agregar_lista_espera]
        )
        chat_session = model.start_chat(enable_automatic_function_calling=True)
        print("DEBUG: Gemini AI initialized with API Key, System Instruction and Tools.")
    else:
        model = None
        print("Warning: GOOGLE_API_KEY not set. AI disabled.")
except Exception as e:
    model = None
    print(f"Error initializing Gemini AI: {e}")

class ChatRequest(BaseModel):
    message: str
    phone: str = None
    session_id: str = "default"

@chatbot_router.post("/message")
async def send_message(request: ChatRequest):
    print(f"DEBUG: Received message: {request.message}")
    
    if not model:
        return {
            "response": "hola! soy saboria. por ahora estoy en mantenimiento, pero te cuento que nuestro risotto es increíble. ¿te ayudo con una reserva?",
            "status": "mock"
        }
    
    # Optional: Check loyalty if phone is provided
    loyalty_info = ""
    if request.phone:
        loyalty = nocodb_service.get_customer_loyalty(request.phone)
        if loyalty["loyalty_tier"] == "VIP":
            loyalty_info = f"[INFO INTERNA: El cliente es {loyalty['customer_name']}, categoría VIP]"

    try:
        # We append context internally if it's a VIP
        full_message = f"{loyalty_info} {request.message}" if loyalty_info else request.message
        
        # When `enable_automatic_function_calling=True`, chat_session handles calling the python
        # function internally and re-prompting the model with the result, 
        # so `response.text` will contain the final natural language answer.
        response = chat_session.send_message(full_message)
        
        # Clean response text (remove any markdown formatting if AI adds it)
        text = response.text.replace("**", "").replace("#", "").strip().lower()
        
        return {"response": text, "status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in Gemini Chat: {e}")
        return {
            "response": "lo siento, tuve un pequeño problema técnico... ¿me podrías repetir eso? me encantaría ayudarte.",
            "status": "error"
        }
