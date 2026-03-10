
import os

file_path = r'c:\Users\emanuel\Desktop\Codigos\caza_2026_v2\caza_2026_v2_backend\main_api.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update get_permisos association
old_block_1 = """        # Buscar PDFs de permisos
        permisos_folder_id = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
        pdfs = drive_services.list_pdfs_in_folder(permisos_folder_id)
        await log_activity('INFO', 'pdfs_found', f"PDFs de permisos: {[pdf.get('name', 'SIN_NOMBRE') for pdf in pdfs[:3]]}")
        pdf_dict = {pdf['name'].replace('.pdf', ''): pdf.get('webViewLink', '') for pdf in pdfs if 'name' in pdf}

        # Enriquecer con estado de pago desde la base de datos
        for permiso in paginated_data:
            permiso_id = safe_str_id(permiso.get('ID'))
            # Asegurar que el ID en el dict sea el sanitizado para el frontend
            if permiso_id:
                permiso['ID'] = permiso_id

            # Asociar PDF
            if permiso_id and permiso_id in pdf_dict:
                permiso['pdf_link'] = pdf_dict[permiso_id]"""

new_block_1 = """        # Buscar PDFs de permisos
        permisos_folder_id = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
        pdfs = drive_services.list_pdfs_in_folder(permisos_folder_id)
        # Diccionario de ID -> Link
        pdf_dict = {pdf['name'].replace('.pdf', '').strip(): pdf.get('webViewLink', '') for pdf in pdfs if 'name' in pdf}

        # 1. Crear un mapeo de DNI -> PDF_LINK basado en todos los registros que SI tienen match directo.
        dni_to_pdf = {}
        if not df.empty:
            for _, row in df.iterrows():
                p_id = safe_str_id(row.get('ID'))
                p_dni = safe_str_id(row.get('DNI o Pasaporte'))
                if p_id and p_dni and p_id in pdf_dict:
                    dni_to_pdf[p_dni] = pdf_dict[p_id]

        # Enriquecer con estado de pago desde la base de datos
        for permiso in paginated_data:
            permiso_id = safe_str_id(permiso.get('ID'))
            permiso_dni = safe_str_id(permiso.get('DNI o Pasaporte'))
            
            # Asegurar que el ID en el dict sea el sanitizado para el frontend
            if permiso_id:
                permiso['ID'] = permiso_id

            # Asociar PDF
            # Prioridad 1: Match directo por ID
            if permiso_id and permiso_id in pdf_dict:
                permiso['pdf_link'] = pdf_dict[permiso_id]
            # Prioridad 2: Match por DNI (si el ID no funcionó pero hay un PDF para ese DNI)
            elif permiso_dni and permiso_dni in dni_to_pdf:
                permiso['pdf_link'] = dni_to_pdf[permiso_dni]"""

# 2. Update send_permiso_email_endpoint association
old_block_2 = """        for pdf in pdfs:
            if 'name' in pdf and safe_str_id(pdf['name'].replace('.pdf', '')) == permiso_id_clean:
                pdf_id = pdf.get('id')
                pdf_filename = pdf.get('name')
                break"""

new_block_2 = """        # Intentar match por ID primero
        for pdf in pdfs:
            if 'name' in pdf and safe_str_id(pdf['name'].replace('.pdf', '')) == permiso_id_clean:
                pdf_id = pdf.get('id')
                pdf_filename = pdf.get('name')
                break
        
        # Si no hubo match por ID, intentar buscar por DNI en el sheet para ver si otro registro sí tiene match
        if not pdf_id:
            try:
                sheet_id = os.getenv("GOOGLE_SHEET_ID")
                df_permisos = sheets_services.read_sheet_data(sheet_id, "permisos")
                # Buscar el DNI del permiso actual
                current_permiso = df_permisos[df_permisos['ID'].astype(str).str.strip() == permiso_id_clean]
                if not current_permiso.empty:
                    dni = safe_str_id(current_permiso.iloc[0].get('DNI o Pasaporte'))
                    if dni:
                        # Buscar otros registros con el mismo DNI que SI tengan un PDF en Drive
                        for _, row in df_permisos.iterrows():
                            other_id = safe_str_id(row.get('ID'))
                            if other_id and safe_str_id(row.get('DNI o Pasaporte')) == dni:
                                for pdf in pdfs:
                                    if 'name' in pdf and safe_str_id(pdf['name'].replace('.pdf', '')) == other_id:
                                        pdf_id = pdf.get('id')
                                        pdf_filename = pdf.get('name')
                                        break
                            if pdf_id: break
            except Exception as e:
                print(f"Error en fallback por DNI: {e}")"""

if old_block_1 in content:
    content = content.replace(old_block_1, new_block_1)
    print("Block 1 updated successfully.")
else:
    print("Block 1 NOT FOUND.")

if old_block_2 in content:
    content = content.replace(old_block_2, new_block_2)
    print("Block 2 updated successfully.")
else:
    print("Block 2 NOT FOUND.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
