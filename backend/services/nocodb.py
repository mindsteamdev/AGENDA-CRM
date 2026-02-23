import requests
import os
from datetime import datetime

class NocoDBService:
    def __init__(self):
        self.api_token = os.getenv("NOCODB_API_TOKEN")
        self.base_url = "https://app.nocodb.com/api/v2"
        self.tables = {
            "bookings": os.getenv("NOCODB_TABLE_BOOKINGS", os.getenv("NOCODB_TABLE_NAME")),
            "waitlist": os.getenv("NOCODB_TABLE_WAITLIST"),
            "customers": os.getenv("NOCODB_TABLE_CUSTOMERS"),
            "resources": os.getenv("NOCODB_TABLE_RESOURCES")
        }

    def _get_headers(self):
        return {
            "xc-token": self.api_token,
            "Content-Type": "application/json"
        }

    def _post_record(self, table_key: str, payload: dict):
        table_id = self.tables.get(table_key)
        if not table_id or not self.api_token:
            print(f"NocoDB: Table ID for {table_key} or API Token not configured.")
            return False

        url = f"{self.base_url}/tables/{table_id}/records"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            print(f"NocoDB HTTP Error posting to {table_key}: {e}")
            print(f"Response content: {e.response.text}")
            return False
        except Exception as e:
            print(f"NocoDB: Error posting to {table_key}: {e}")
            return False

    def _get_records(self, table_key: str, params: dict = None):
        table_id = self.tables.get(table_key)
        if not table_id or not self.api_token:
            return None

        url = f"{self.base_url}/tables/{table_id}/records"
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"NocoDB: Error getting from {table_key}: {e}")
            return None

    def sync_booking(self, booking_data: dict):
        """Synchronizes a booking record to NocoDB."""
        payload = {
            "customer_name": booking_data.get("customer_name"),
            "customer_phone": booking_data.get("customer_phone"),
            "booking_time": booking_data.get("booking_time"),
            "party_size": booking_data.get("party_size")
        }
        return self._post_record("bookings", payload)

    def add_to_waitlist(self, waitlist_data: dict) -> bool:
        """
        Agrega un cliente a la lista de espera en NocoDB.
        Llamada por el chatbot cuando un cliente acepta unirse.
        """
        import os
        import requests

        # Obtener configuración de variables de entorno
        url_base = os.getenv("NOCODB_URL")
        api_token = os.getenv("NOCODB_API_TOKEN")
        table_id = os.getenv("NOCODB_WAITLIST_TABLE_ID")

        if not all([url_base, api_token, table_id]):
            print("NocoDB Waitlist Error: Faltan variables de entorno (URL, Token o Table ID).")
            return False

        # Construir endpoint según requerimiento
        url = f"{url_base}/api/v2/tables/{table_id}/records"
        
        headers = {
            "xc-token": api_token,
            "Content-Type": "application/json"
        }

        try:
            # POST a la API de NocoDB
            response = requests.post(url, headers=headers, json=waitlist_data)
            
            # Retornar True si el código es exitoso (200 o 201)
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"NocoDB API Error (Status {response.status_code}): {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            # Manejar errores de red e imprimir para depuración
            print(f"Error de red al conectar con NocoDB Waitlist: {e}")
            return False

    def get_customer_loyalty(self, phone: str):
        """Queries the customers table to find loyalty tier and name."""
        params = {
            "where": f"(phone,eq,{phone})"
        }
        records = self._get_records("customers", params)
        if records and records.get("list"):
            customer = records["list"][0]
            return {
                "loyalty_tier": customer.get("loyalty_tier", "Standard"),
                "customer_name": customer.get("name", "Cliente")
            }
        return {"loyalty_tier": "Standard", "customer_name": "Invitado"}

    def create_customer_if_not_exists(self, phone: str, name: str) -> bool:
        """Helper to create a customer record if they don't already exist."""
        # Check if exists using existing method (it returns 'Invitado' if not found)
        customer_info = self.get_customer_loyalty(phone)
        if customer_info["customer_name"] == "Invitado":
            print(f"NocoDB: Cliente {phone} no existe. Sincronizando nuevo registro.")
            payload = {
                "name": name,
                "phone": phone,
                "loyalty_tier": "Standard"
            }
            return self._post_record("customers", payload)
        
        print(f"NocoDB: Cliente {phone} ya existe como {customer_info['customer_name']}. Saltando sincronización.")
        return True # Ya existía, todo bien

    def check_resource_availability(self, party_size: int, booking_time: str):
        """
        Calcula la disponibilidad real sumando los asientos ya reservados a esa misma fecha.
        Obtenemos todas las reservas y filtramos en Python para evitar problemas de 
        formateo en la cláusula SQL/Where de NocoDB.
        """
        max_capacity = int(os.getenv("MAX_RESTAURANT_CAPACITY", 5)) # Default to 5 for test safety or env
        
        # Extraemos la fecha (YYYY-MM-DD) del string recibido
        date_only = booking_time[:10]
        
        # Consultamos TODAS las reservas (limitamos a 1000 para seguridad)
        params = {
            "limit": 1000
        }
        records = self._get_records("bookings", params)
        
        current_booked = 0
        if records and isinstance(records.get("list"), list):
            print(f"DEBUG NOCODB: Procesando {len(records['list'])} reservas totales...")
            for booking in records["list"]:
                # Verificamos si la reserva coincide con la fecha
                b_time = str(booking.get("booking_time", ""))
                if date_only in b_time:
                    try:
                        pax = int(booking.get("party_size", 0))
                        current_booked += pax
                    except:
                        pass
        
        print(f"DEBUG NOCODB: Total reservado para el día {date_only}: {current_booked}")
                
        if (current_booked + party_size) <= max_capacity:
            return True
            
        print(f"NocoDB: Capacidad excedida para el {date_only}. Aforo Disp: {max_capacity}, Ya Reservados: {current_booked}, Intentando Reservar: {party_size}")
        return False

    def get_next_waiting_customer(self):
        """
        Busca el siguiente cliente en la lista de espera que aún no ha sido notificado.
        """
        params = {
            "limit": 100, # Traemos varios y filtramos en Python para mayor precisión con NULLs
            "sort": "Id"
        }
        records = self._get_records("waitlist", params)
        if records and records.get("list"):
            # Filtramos el primero que no sea 'Notificado'
            for record in records["list"]:
                if record.get("status") != "Notificado" and record.get("customer_phone"):
                    return record
        return None

    def update_waitlist_status(self, record_id: int, status: str):
        """
        Actualiza el estado de un registro en la lista de espera.
        """
        table_id = self.tables.get("waitlist")
        if not table_id or not self.api_token:
            return False

        url = f"{self.base_url}/tables/{table_id}/records"
        payload = {
            "Id": record_id,
            "status": status
        }
        try:
            # NocoDB v2 usa PATCH para updates parciales por ID
            response = requests.patch(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"NocoDB: Error updating waitlist status: {e}")
            return False

nocodb_service = NocoDBService()
