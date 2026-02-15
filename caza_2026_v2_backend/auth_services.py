import os
import json # Importar el módulo json
from google.oauth2 import service_account
from googleapiclient import discovery

# Define los 'scopes' o permisos que nuestra aplicación solicitará.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets", # Este scope incluye lectura y escritura
    "https://www.googleapis.com/auth/drive"         # Este scope incluye lectura y escritura para Drive
]

# Nombre del archivo JSON de la clave de la cuenta de servicio (como fallback)
SERVICE_ACCOUNT_FILE = "service_account.json"

def get_google_credentials():
    """
    Carga las credenciales de la cuenta de servicio.
    Prioriza la variable de entorno GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON.
    Si no está presente, intenta cargar desde el archivo service_account.json.
    """
    credentials_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON")

    if credentials_json_str:
        try:
            credentials_info = json.loads(credentials_json_str)
            creds = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES
            )
            return creds
        except json.JSONDecodeError as e:
            raise ValueError(
                f"La variable de entorno GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON "
                f"no contiene un JSON válido: {e}"
            )
        except Exception as e:
            raise Exception(
                f"Error al cargar credenciales desde GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON: {e}"
            )
    else:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(
                f"El archivo de clave de la cuenta de servicio '{SERVICE_ACCOUNT_FILE}' no se encontró "
                "y la variable de entorno GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON no está configurada. "
                "Asegúrate de haber configurado uno de ellos."
            )

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return creds

if __name__ == '__main__':
    # Este bloque de código es para probar que la autenticación funciona.
    try:
        credentials = get_google_credentials()
        print("¡Autenticación con Cuenta de Servicio exitosa!")

        # Opcional: Probar la conexión creando un servicio de Drive
        drive_service = discovery.build('drive', 'v3', credentials=credentials)
        print("Servicio de Google Drive creado exitosamente.")

        # Opcional: Probar la conexión creando un servicio de Sheets
        sheets_service = discovery.build('sheets', 'v4', credentials=credentials)
        print("Servicio de Google Sheets creado exitosamente.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error de configuración de credenciales: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la autenticación: {e}")

