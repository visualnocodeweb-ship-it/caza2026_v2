import sys
import os
sys.path.append(r"c:\Users\emanuel\Desktop\Codigos\caza_2026_v2\caza_2026_v2_backend")
import pdf_generator

datos_mock = {
    "Nombre y Apellido": "Juan Perez",
    "DNI": "12345678",
    "Categoria": "Comercial residente en la Provincia NQN",
    "Fecha Emision": "2026-05-25",
    "Vigencia": "Hasta 2026-12-31"
}

pdf_bytes = pdf_generator.generate_permiso_menor_pdf("9999", datos_mock, "Juan Perez")

out_path = r"C:\Users\emanuel\.gemini\antigravity\brain\2a6a07a3-2b71-4e01-81ef-b19bf4ce9b44\Permiso_Ejemplo.pdf"
with open(out_path, "wb") as f:
    f.write(pdf_bytes)

print("PDF generated at", out_path)
