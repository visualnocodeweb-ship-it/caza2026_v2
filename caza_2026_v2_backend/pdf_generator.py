import os
import qrcode
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import tempfile

def generate_permiso_menor_pdf(permiso_id: str, datos_completos: dict, nombre_cazador: str = "") -> bytearray:
    pdf = FPDF()
    pdf.add_page()
    
    # Header Image
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    img_path = os.path.join(assets_dir, "Guardafauna_1.png")
    
    if os.path.exists(img_path):
        pdf.image(img_path, x=10, y=10, w=190)
        pdf.ln(50)
    else:
        pdf.ln(20)
    
    # Title
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(190, 10, text="Permiso de Caza Menor Temporada 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)
    
    # ID
    pdf.set_font("helvetica", 'B', 12)
    
    # Use numero_secuencial if available, otherwise fallback to original ID
    seq_num = datos_completos.get('numero_secuencial')
    if seq_num is not None:
        formatted_id = f"2026-{str(seq_num).zfill(2)}"
    else:
        formatted_id = f"2026-{permiso_id.zfill(2)}" if permiso_id.isdigit() else f"2026-{permiso_id}"
        
    pdf.cell(190, 10, text=f"ID Único de Permiso: {formatted_id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)
    
    # Data table
    pdf.set_font("helvetica", size=10)
    
    ignored_keys_lower = [
        'id', 'estado de cobro enviado', 'estado de pago', 'payment_id', 'fecha_pago', 'sent_statuses',
        'foto dni', 'autorización establecimiento', 'completado por', 'autorizacion establecimiento',
        'numero_secuencial', 'marca temporal', 'timestamp'
    ]
    
    # Exact matches for duplicates to ignore
    ignored_keys_exact = [
        'Nombre y Apellido', 'Dirección de correo electrónico', 'Categoría', 'WhatsApp', 'ACM', 'DNI', 'Fecha Inicio Permiso'
    ]
    
    # Add a bit of left margin for the table
    table_margin = 15
    pdf.set_x(table_margin)
    
    for key, value in datos_completos.items():
        key_str = str(key)
        if key_str.lower() not in ignored_keys_lower and key_str not in ignored_keys_exact:
            pdf.set_font("helvetica", 'B', 10)
            pdf.cell(60, 8, text=key_str+":", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            
            pdf.set_font("helvetica", '', 10)
            val_str = str(value) if value is not None and str(value).strip() != "" else "-"
            pdf.multi_cell(120, 8, text=val_str, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(table_margin)
            
    # QR Code
    qr_data = "https://docs.google.com/drawings/d/1u6crd9FJkofF1dDz1bItiYVYhS9UnMk02g2Jo5I4M_k/edit?usp=sharing"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr_path = tmp.name
        img_qr.save(qr_path)
        
    pdf.ln(10)
    # Check if we need to add a page to fit the QR
    if pdf.get_y() > 220:
        pdf.add_page()
        
    x = (210 - 40) / 2
    pdf.image(qr_path, x=x, w=40)
    
    os.remove(qr_path)
    
    return bytes(pdf.output())
