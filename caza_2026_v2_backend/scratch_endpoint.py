
class DownloadPermisoPdfRequest(BaseModel):
    permiso_id: str
    nombre_apellido: str
    datos_completos: dict

from fastapi.responses import Response

@app.post("/api/permisos-menor/pdf")
async def download_permiso_menor_pdf(request_data: DownloadPermisoPdfRequest):
    try:
        import pdf_generator
        pdf_content = pdf_generator.generate_permiso_menor_pdf(
            request_data.permiso_id,
            request_data.datos_completos,
            request_data.nombre_apellido
        )
        pdf_filename = f"Permiso_Menor_{request_data.nombre_apellido.replace(' ', '_')}_{request_data.permiso_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
        )
    except Exception as e:
        await log_activity('ERROR', 'download_pdf_failed', f"Error generando PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
