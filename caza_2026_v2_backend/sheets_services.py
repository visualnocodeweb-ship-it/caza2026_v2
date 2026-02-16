import logging
from googleapiclient import discovery
from .auth_services import get_google_credentials
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv(encoding='latin-1') # Cargar variables de entorno del archivo .env

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

# Configurar el logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Caché del servicio de Sheets
_cached_sheets_service = None

def get_sheets_service():
    """Obtiene y devuelve un objeto de servicio de Google Sheets. Usa caché."""
    global _cached_sheets_service
    if _cached_sheets_service:
        return _cached_sheets_service

    credentials = get_google_credentials()
    service = discovery.build('sheets', 'v4', credentials=credentials)
    _cached_sheets_service = service
    return service

def read_sheet_data(sheet_id, sheet_name):
    """
    Lee los datos de una hoja de cálculo específica de Google Sheets y los devuelve como un DataFrame de Pandas.
    """
    service = get_sheets_service()
    
    # Manejar el nombre de la hoja para la API de Google Sheets
    if ' ' in sheet_name or "'" in sheet_name:
        # Si el nombre de la hoja contiene espacios o comillas, encerrarlo en comillas simples.
        # Además, si ya hay comillas, escaparlas.
        processed_sheet_name = sheet_name.replace("'", "''") # Escapar comillas simples
        range_name = f"'{processed_sheet_name}'!A:ZZ"
    else:
        # Si no hay espacios ni comillas, se puede usar directamente.
        range_name = f"{sheet_name}!A:ZZ"

    if not sheet_id or not sheet_name:
        logging.error("Error: GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no están configurados en .env")
        return pd.DataFrame()

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        if not values or len(values) < 2:
            logging.warning(f"No se encontraron datos o solo se encontró la fila de encabezados en la hoja '{sheet_name}'.")
            return pd.DataFrame()

        headers = [h.strip() for h in values[0]]
        data_rows = values[1:]
        
        # Ensure all rows have the same number of columns as the headers, padding with empty strings
        num_headers = len(headers)
        processed_rows = []
        for row in data_rows:
            # Pad the row with empty strings if it has fewer columns than headers
            while len(row) < num_headers:
                row.append('')
            processed_rows.append(row[:num_headers])

        if not processed_rows:
            return pd.DataFrame(columns=headers)

        df = pd.DataFrame(processed_rows, columns=headers)
        return df
    except Exception as e:
        logging.error(f"Error al leer datos de la hoja {sheet_id}/{sheet_name}: {e}", exc_info=True)
        raise

def append_sheet_data(sheet_id, sheet_name, values):
    """
    Agrega filas de datos a una hoja de cálculo específica de Google Sheets.

    Args:
        sheet_id (str): El ID de la hoja de cálculo de Google.
        sheet_name (str): El nombre de la pestaña dentro de la hoja de cálculo (ej. 'Hoja1').
        values (list of list): Una lista de listas, donde cada sub-lista es una fila de datos a agregar.

    Returns:
        dict: El resultado de la operación de la API de Google Sheets.
    """
    service = get_sheets_service()
    range_name = f"'{sheet_name}'"

    body = {
        'values': values
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()
    return result

def update_payment_status(sheet_id, sheet_name, inscription_id, new_status):
    """
    Actualiza el estado de pago de una inscripción en la hoja de Google.
    Encuentra la fila por 'numero_inscripcion' y actualiza la columna 'Estado de Pago'.
    """
    service = get_sheets_service()
    range_name = f"'{sheet_name}'!A:ZZ"

    try:
        # 1. Leer toda la hoja para encontrar la fila y la columna
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            logging.error(f"Error: La hoja '{sheet_name}' está vacía.")
            return None

        headers = [h.strip() for h in values[0]] # Limpiar encabezados
        try:
            id_col_index = headers.index('numero_inscripcion')
            status_col_index = headers.index('Estado de Pago')
        except ValueError as e:
            logging.error(f"Error: No se encontró la columna 'numero_inscripcion' o 'Estado de Pago' en los encabezados: {e}", exc_info=True)
            return None

        # 2. Encontrar el número de fila (row_number)
        row_number = -1
        for i, row in enumerate(values[1:], start=2): # Empezar desde la fila 2
            if len(row) > id_col_index and row[id_col_index].strip() == inscription_id.strip(): # Limpiar valor para comparación
                row_number = i
                break
        
        if row_number == -1:
            logging.warning(f"Error: No se encontró la inscripción con ID '{inscription_id}'.")
            return None

        # 3. Actualizar la celda
        # La columna se convierte a letra (A, B, C...)
        status_col_letter = chr(ord('A') + status_col_index)
        update_range = f"'{sheet_name}'!{status_col_letter}{row_number}"
        
        body = {
            'values': [[new_status]]
        }
        update_result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=update_range,
            valueInputOption="RAW",
            body=body
        ).execute()
        
        logging.info(f"Éxito: Se actualizó la inscripción '{inscription_id}' a '{new_status}'.")
        return update_result

    except Exception as e:
        logging.error(f"Error al actualizar el estado del pago para la inscripción {inscription_id}: {e}", exc_info=True)
        return None

def update_cobro_enviado_status(sheet_id, sheet_name, permiso_id, new_status):
    """
    Actualiza el estado de cobro enviado de un permiso en la hoja de Google.
    Encuentra la fila por 'ID' y actualiza la columna 'Estado de Cobro Enviado'.
    """
    service = get_sheets_service()
    range_name = f"'{sheet_name}'!A:ZZ"

    try:
        # 1. Leer toda la hoja para encontrar la fila y la columna
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            logging.error(f"Error: La hoja '{sheet_name}' está vacía.")
            return None

        headers = [h.strip() for h in values[0]] # Limpiar encabezados
        try:
            id_col_index = headers.index('ID')
            status_col_index = headers.index('Estado de Cobro Enviado')
        except ValueError as e:
            logging.error(f"Error: No se encontró la columna 'ID' o 'Estado de Cobro Enviado' en los encabezados: {e}", exc_info=True)
            return None

        # 2. Encontrar el número de fila (row_number)
        row_number = -1
        for i, row in enumerate(values[1:], start=2): # Empezar desde la fila 2
            if len(row) > id_col_index and row[id_col_index].strip() == permiso_id.strip(): # Limpiar valor para comparación
                row_number = i
                break
        
        if row_number == -1:
            logging.warning(f"Error: No se encontró el permiso con ID '{permiso_id}'.")
            return None

        # 3. Actualizar la celda
        # La columna se convierte a letra (A, B, C...)
        status_col_letter = chr(ord('A') + status_col_index)
        update_range = f"'{sheet_name}'!{status_col_letter}{row_number}"
        
        body = {
            'values': [[new_status]]
        }
        update_result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=update_range,
            valueInputOption="RAW",
            body=body
        ).execute()
        
        logging.info(f"Éxito: Se actualizó el permiso '{permiso_id}' a '{new_status}'.")
        return update_result

    except Exception as e:
        logging.error(f"Error al actualizar el estado del cobro enviado para el permiso {permiso_id}: {e}", exc_info=True)
        return None


def get_price_for_establishment(sheet_id_param, sheet_name_param, tipo_establecimiento):
    """
    Obtiene el precio de la hoja 'precios' basado en el tipo de establecimiento.

    Args:
        sheet_id_param (str): El ID de la hoja de cálculo de precios.
        sheet_name_param (str): El nombre de la pestaña de precios.
        tipo_establecimiento (str): El tipo de establecimiento ('Area Libre' o 'Criadero').

    Returns:
        float: El precio correspondiente.
    """
    # Usar PRICES_SHEET_ID si está definido, de lo contrario, usar sheet_id_param
    price_sheet_id = os.getenv("PRICES_SHEET_ID", sheet_id_param)
    price_sheet_name = "precios" # Nombre de la pestaña de precios, según el usuario

    precios_df = read_sheet_data(price_sheet_id, price_sheet_name)
    logging.info(f"Columnas del DataFrame de precios: {precios_df.columns.tolist()}")

    if precios_df.empty:
        raise ValueError("No se pudieron leer los datos de la hoja de precios.")

    # Mapeo de tipo de establecimiento a la descripción en la hoja de precios
    actividad_map = {
        'Area Libre': 'Establecimientos Area Libre',
        'Criadero': 'Establecimientos Criadero'
    }

    actividad = actividad_map.get(tipo_establecimiento)
    if not actividad:
        raise ValueError(f"Tipo de establecimiento no válido: {tipo_establecimiento}")

    # Buscar el precio en el DataFrame
    # Limpiar también los valores de la columna 'Actividad' antes de comparar
    precio_row = precios_df[precios_df['Actividad'].apply(lambda x: x.strip() if isinstance(x, str) else x) == actividad.strip()]

    if precio_row.empty:
        raise ValueError(f"No se encontró el precio para la actividad: '{actividad}' después de limpiar los espacios.")

    # Obtener el valor de la columna 'Valor'. Usamos .get() para evitar KeyError y manejar mejor el error.
    precio_str = precio_row.iloc[0].get('Valor')
    
    if precio_str is None:
        raise ValueError(f"La columna 'Valor' no se encontró o está vacía para la actividad '{actividad}'. Columnas disponibles: {precios_df.columns.tolist()}")

    # Limpiar y convertir el precio
    cleaned_price_str = str(precio_str).replace('$', '').replace(',', '').strip()
    return float(cleaned_price_str)


def get_price_for_categoria(sheet_id_param, sheet_name_param, categoria):
    """
    Obtiene el precio de la hoja 'precios' basado en la categoría del permiso.

    Args:
        sheet_id_param (str): El ID de la hoja de cálculo de precios.
        sheet_name_param (str): El nombre de la pestaña de precios.
        categoria (str): La categoría del permiso.

    Returns:
        float: El precio correspondiente.
    """
    # Usar PRICES_SHEET_ID si está definido, de lo contrario, usar sheet_id_param
    price_sheet_id = os.getenv("PRICES_SHEET_ID", sheet_id_param)
    price_sheet_name = "precios" # Nombre de la pestaña de precios, según el usuario

    precios_df = read_sheet_data(price_sheet_id, price_sheet_name)
    logging.info(f"Columnas del DataFrame de precios: {precios_df.columns.tolist()}")

    if precios_df.empty:
        raise ValueError("No se pudieron leer los datos de la hoja de precios.")

    # Buscar el precio en el DataFrame
    precio_row = precios_df[precios_df['Actividad'].apply(lambda x: x.strip() if isinstance(x, str) else x) == categoria.strip()]

    if precio_row.empty:
        raise ValueError(f"No se encontró el precio para la categoría: '{categoria}' después de limpiar los espacios.")

    # Obtener el valor de la columna 'Valor'. Usamos .get() para evitar KeyError y manejar mejor el error.
    precio_str = precio_row.iloc[0].get('Valor')
    
    if precio_str is None:
        raise ValueError(f"La columna 'Valor' no se encontró o está vacía para la categoría '{categoria}'. Columnas disponibles: {precios_df.columns.tolist()}")

    # Limpiar y convertir el precio
    cleaned_price_str = str(precio_str).replace('$', '').replace(',', '').strip()
    return float(cleaned_price_str)



if __name__ == '__main__':
    # Bloque de prueba para la función read_sheet_data
    logging.info("Probando la función read_sheet_data...")
    if GOOGLE_SHEET_ID == "ID_DE_TU_HOJA_AQUI" or GOOGLE_SHEET_NAME == "NOMBRE_DE_TU_HOJA_AQUI":
        logging.warning("Por favor, configura GOOGLE_SHEET_ID y GOOGLE_SHEET_NAME en tu archivo .env antes de probar.")
    else:
        try:
            sheet_df = read_sheet_data(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME)
            if not sheet_df.empty:
                logging.info(f"Se leyeron {len(sheet_df)} filas de la hoja '{GOOGLE_SHEET_NAME}':")
                logging.info(sheet_df.head()) # Mostrar las primeras 5 filas
            else:
                logging.warning("No se pudo leer la hoja de cálculo o está vacía.")
        except Exception as e:
            logging.error(f"Error durante la prueba de read_sheet_data: {e}", exc_info=True)
