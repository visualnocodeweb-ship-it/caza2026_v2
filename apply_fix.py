import os

target_file = 'c:/Users/emanuel/Desktop/Codigos/caza_2026_v2/caza_2026_v2_backend/main_api.py'
with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. get_inscripciones return (add debug_search)
old_ret_inscrip = """        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }"""
new_ret_inscrip = """        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "debug_search": debug_search if 'debug_search' in locals() else "None"
        }"""

# 2. get_permisos and get_reses search block
# These have the same structure
old_search_block = """        # Aplicar búsqueda global si hay término
        if search:
            search_str = search.lower()
            mask = df.apply(lambda row: row.astype(str).str.contains(search_str, case=False).any(), axis=1)
            df = df[mask]"""

new_search_block = """        # Aplicar búsqueda global si hay término
        debug_search = f"Received: {search}"
        if search and str(search).strip():
            search_str = str(search).lower()
            # Método más robusto para filtrar en todas las columnas
            mask = df.astype(str).apply(lambda x: x.str.contains(search_str, case=False)).any(axis=1)
            df = df[mask]"""

# 3. get_permisos and get_reses return
# Same as inscrip

# Perform replacements
# We use replace once for each because we know they are identical

# Inscriptions return
content = content.replace(old_ret_inscrip, new_ret_inscrip, 1)

# Permisos and Reses blocks (replace both)
content = content.replace(old_search_block, new_search_block)

# Permisos and Reses returns (after blocks)
# We can't use replace(..., 2) easily because it might hit others?
# Actually, those 3 endpoints are the only ones with that exact return structure and variable names.
# Wait, let's just do it carefully.
content = content.replace(old_ret_inscrip, new_ret_inscrip)

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement complete.")
