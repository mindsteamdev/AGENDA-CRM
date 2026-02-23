from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from backend.services.data import get_bq_client
from backend.services.nocodb import nocodb_service
import os
import uuid
from twilio.rest import Client

booking_router = APIRouter()

def enviar_whatsapp(nombre: str, telefono: str) -> bool:
    """
    Función auxiliar para enviar un mensaje de WhatsApp usando Twilio.
    """
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not all([account_sid, auth_token, from_whatsapp]):
            print("Error: Credenciales de Twilio no configuradas en el entorno.")
            return False

        client = Client(account_sid, auth_token)
        
        # Asegurar prefijo whatsapp: para Twilio
        to_number = telefono if telefono.startswith("whatsapp:") else f"whatsapp:{telefono}"
        
        message_body = f"¡Hola {nombre}, tu mesa en Sabor Divino está lista!"
        
        message = client.messages.create(
            body=message_body,
            from_=from_whatsapp,
            to=to_number
        )
        
        print(f"Twilio: Mensaje enviado con SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Twilio Error: Falló el envío a {telefono}. Detalle: {e}")
        return False

class BookingCreate(BaseModel):
    customer_name: str
    customer_phone: str
    booking_time: datetime
    party_size: int

@booking_router.post("/")
async def create_booking(booking: BookingCreate):
    booking_id = str(uuid.uuid4())
    
    # 0. Check Resource Availability (Option 5)
    is_available = nocodb_service.check_resource_availability(booking.party_size, booking.booking_time.isoformat())
    if not is_available:
        return {
            "status": "full",
            "message": "Lo sentimos, no hay disponibilidad para esa hora. ¿Desea unirse a la lista de espera?",
            "booking_details": booking
        }

    # 1. Log to console (simulating operational DB)
    print(f"New Booking: {booking_id} - {booking}")
    
    # 2. Insert into BigQuery for analytics
    # ... (existing BigQuery logic)
    client = get_bq_client()
    bq_status = "skipped"
    if client:
        dataset_id = "restaurant_ops"
        project_id = "gen-lang-client-0344019036"
        table_id = f"{project_id}.{dataset_id}.bookings"
        
        rows_to_insert = [
            {
                "booking_id": booking_id,
                "customer_name": booking.customer_name,
                "customer_phone": booking.customer_phone,
                "booking_time": booking.booking_time.isoformat(),
                "party_size": booking.party_size,
                "created_at": datetime.now().isoformat()
            }
        ]
        
        try:
            errors = client.insert_rows_json(table_id, rows_to_insert)
            bq_status = "success" if not errors else "error"
        except Exception as e:
            print(f"BigQuery exception: {e}")
            bq_status = "failed"

    # 3. Mirror to NocoDB CRM
    booking_sync_data = {
        "booking_id": booking_id,
        "customer_name": booking.customer_name,
        "customer_phone": booking.customer_phone,
        "booking_time": booking.booking_time.isoformat(),
        "party_size": booking.party_size
    }
    nocodb_service.sync_booking(booking_sync_data)

    return {
        "status": "success", 
        "booking_id": booking_id, 
        "details": booking, 
        "bigquery_status": bq_status
    }

@booking_router.post("/waitlist")
async def join_waitlist(waitlist_entry: BookingCreate):
    """
    Endpoint to join the waitlist (Option 2).
    """
    success = nocodb_service.add_to_waitlist(waitlist_entry.dict())
    if success:
        return {"status": "success", "message": "Te hemos añadido a la lista de espera. Te avisaremos si se libera un espacio."}
    else:
        raise HTTPException(status_code=500, detail="Error al unirse a la lista de espera")

@booking_router.post("/webhook")
async def dialogflow_webhook(request: dict):
    """
    Webhook handler for Dialogflow CX.
    It expects a WebhookRequest JSON from Dialogflow CX.
    """
    print(f"Dialogflow Webhook received: {request}")
    
    # 1. Extract session parameters
    # In Dialogflow CX, parameters are inside 'sessionInfo' -> 'parameters'
    session_info = request.get("sessionInfo", {})
    parameters = session_info.get("parameters", {})
    
    # 2. Extract specific fields
    customer_name = parameters.get("customer_name", "Cliente")
    customer_phone = parameters.get("customer_phone", "000000000")
    
    # Check Loyalty (Option 3)
    loyalty_info = nocodb_service.get_customer_loyalty(customer_phone)
    tier = loyalty_info.get("loyalty_tier", "Nuevo") if loyalty_info else "Nuevo"
    
    greeting_prefix = f"¡Qué gusto verte de nuevo! Como cliente {tier}, " if tier != "Nuevo" else ""

    # Date and Time handling
    booking_date = parameters.get("date")
    booking_time_str = parameters.get("time")
    party_size = parameters.get("party_size", 2)
    
    if not booking_date or not booking_time_str:
        return {
            "fulfillment_response": {
                "messages": [{"text": {"text": [f"{greeting_prefix}Lo siento, no pude capturar la fecha u hora correctamente. ¿Podría repetirlos?"]}}]
            }
        }

    try:
        dt_str = f"{booking_date.split('T')[0]}T{booking_time_str.split('T')[1]}"
        booking_dt = datetime.fromisoformat(dt_str)
    except Exception as e:
        print(f"Error parsing date/time: {e}")
        return {
            "fulfillment_response": {
                "messages": [{"text": {"text": ["Hubo un error al procesar la fecha y hora. Por favor intente de nuevo."]}}]
            }
        }

    # 3. Create booking using existing logic
    booking_data = BookingCreate(
        customer_name=customer_name,
        customer_phone=customer_phone,
        booking_time=booking_dt,
        party_size=int(party_size)
    )
    
    result = await create_booking(booking_data)
    
    # 4. Handle results (including Capacity/Waitlist)
    if result["status"] == "full":
        response_text = f"{greeting_prefix}{result['message']}"
    else:
        response_text = f"{greeting_prefix}Perfecto {customer_name}, su reserva para {party_size} personas el día {booking_dt.strftime('%d de %B a las %H:%M')} ha sido confirmada. ¡Le esperamos!"
    
    return {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response_text]}}]
        }
    }
@booking_router.post("/notify-next-waitlist")
async def notify_next_waitlist():
    """
    Endpoint para buscar al siguiente cliente en la lista de espera y notificarle.
    """
    try:
        # 1. Llamar al servicio de NocoDB para obtener al siguiente cliente
        cliente = nocodb_service.get_next_waiting_customer()
        
        if not cliente:
            return {
                "message": "La lista de espera está vacía o todos han sido notificados.", 
                "status": "empty"
            }

        # 2. Intentar enviar mensaje real vía Twilio
        nombre = cliente.get('customer_name', 'Cliente')
        telefono = cliente.get('customer_phone')
        record_id = cliente.get('Id')

        whatsapp_enviado = enviar_whatsapp(nombre, telefono)

        if not whatsapp_enviado:
            raise HTTPException(
                status_code=500,
                detail=f"Error al enviar notificación por WhatsApp a {nombre}. No se ha actualizado el estado de la lista."
            )

        # 3. Solo si el mensaje se envió, marcar como notificado en NocoDB
        success_update = nocodb_service.update_waitlist_status(record_id, 'Notificado')
        
        if success_update:
            return {
                "message": f"Notificación enviada a {nombre} y estado actualizado.", 
                "status": "success", 
                "customer": nombre
            }
        else:
            # Este caso es crítico: se envió mensaje pero falló registro
            raise HTTPException(
                status_code=500, 
                detail=f"Mensaje enviado a {nombre}, pero no se pudo actualizar el estado en NocoDB."
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en notify-next-waitlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))
