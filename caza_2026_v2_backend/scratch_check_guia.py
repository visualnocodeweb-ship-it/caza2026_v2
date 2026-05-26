import os
import sys
import pandas as pd

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from sheets_services import read_sheet_data
    from dotenv import load_dotenv
    load_dotenv()

    sheet_id = "1Hl99DUx5maPEHkC5JNJqq2SZLa8UgVQBJbeia5jk1VI"
    tab_name = "cabeza_1"
    guia_id = "gt1_fau69dfdc5724244"

    print(f"Buscando guía {guia_id} en {tab_name}...")
    df = read_sheet_data(sheet_id, tab_name)
    
    if df.empty:
        print("La hoja está vacía.")
        sys.exit(0)

    # Buscar el registro
    row = df[df['ID'].astype(str) == str(guia_id)]
    
    if row.empty:
        print(f"No se encontró la guía {guia_id}")
        # Mostrar algunos IDs para debug
        print("IDs disponibles (primeros 5):", df['ID'].head().tolist())
    else:
        data = row.iloc[0].to_dict()
        print("Datos encontrados:")
        for k, v in data.items():
            print(f"  {k}: {v}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
