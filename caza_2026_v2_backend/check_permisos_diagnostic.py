
import os
import sys
from dotenv import load_dotenv

# Importar servicios directamente ya que estamos en el directorio backend
import drive_services
import sheets_services

def main():
    load_dotenv('.env')
    
    permisos_folder_id = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
    print(f"Listando PDFs en la carpeta: {permisos_folder_id}")
    
    try:
        pdfs = drive_services.list_pdfs_in_folder(permisos_folder_id)
        print(f"Total de PDFs encontrados: {len(pdfs)}")
        if not pdfs:
            print("No se encontraron archivos PDF en la carpeta especificada.")
        for pdf in pdfs[:20]: # Mostrar los primeros 20
            print(f"- '{pdf.get('name')}' (ID: {pdf.get('id')})")
            
        # Ahora leer una muestra de la hoja de cálculo de permisos para ver los IDs
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        permisos_tab_name = "permisos"
        print(f"\nLeyendo IDs de la hoja '{permisos_tab_name}' en {sheet_id}...")
        df = sheets_services.read_sheet_data(sheet_id, permisos_tab_name)
        if not df.empty:
            print("Primeros 5 IDs en Sheets:")
            for idx, row in df.tail(5).iterrows():
                print(f"- ID: '{row.get('ID')}' | Nombre: {row.get('Nombre y Apellido')}")
        else:
            print("La hoja de permisos está vacía.")
            
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
