import os
from dotenv import load_dotenv
import mercadopago

# Carga las variables de entorno desde el archivo .env
load_dotenv()

MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

if not MERCADOPAGO_ACCESS_TOKEN:
    raise ValueError("MERCADOPAGO_ACCESS_TOKEN environment variable not set.")

# Inicializa el SDK de MercadoPago
sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

def create_payment_preference(title: str, price: float, external_reference: str, payer_email: str = None) -> dict:
    """
    Crea una preferencia de pago en MercadoPago y retorna el link de pago.

    Args:
        title (str): Título del item (ej. "Inscripción Area Libre")
        price (float): Precio del item
        external_reference (str): Referencia externa (ej. numero_inscripcion o permiso_id)
        payer_email (str, optional): Email del pagador

    Returns:
        dict: {"success": bool, "init_point": str, "preference_id": str, "error": str}
    """
    try:
        preference_data = {
            "items": [
                {
                    "title": title,
                    "quantity": 1,
                    "unit_price": price,
                    "currency_id": "ARS"  # Pesos argentinos
                }
            ],
            "external_reference": external_reference,
            "back_urls": {
                "success": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/pago-exitoso",
                "failure": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/pago-fallido",
                "pending": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/pago-pendiente"
            },
            "auto_return": "approved",
            "notification_url": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/pagos/webhook"
        }

        # Añadir email del pagador si está disponible
        if payer_email:
            preference_data["payer"] = {
                "email": payer_email
            }

        # Crear la preferencia en MercadoPago
        preference_response = sdk.preference().create(preference_data)

        # Debug: Imprimir la respuesta completa
        print(f"DEBUG - Respuesta completa de MercadoPago: {preference_response}")

        # Verificar si la respuesta fue exitosa
        if preference_response.get("status") not in [200, 201]:
            error_msg = preference_response.get("response", {}).get("message", "Error desconocido")
            raise Exception(f"MercadoPago error: {error_msg}")

        # La respuesta puede estar en diferentes niveles según la versión del SDK
        preference = preference_response.get("response")
        if not preference:
            raise Exception(f"No se encontró 'response' en la respuesta de MercadoPago: {preference_response}")

        # Verificar que tenga los campos necesarios
        if "id" not in preference or "init_point" not in preference:
            raise Exception(f"Respuesta de MercadoPago incompleta. Respuesta: {preference}")

        print(f"Preferencia de pago creada. ID: {preference['id']}")

        return {
            "success": True,
            "init_point": preference["init_point"],  # Link de pago
            "preference_id": preference["id"],
            "error": None
        }

    except Exception as e:
        print(f"Error al crear preferencia de pago: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "init_point": None,
            "preference_id": None,
            "error": str(e)
        }
