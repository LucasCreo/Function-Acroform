#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REST API para agregar campos de imagen a archivos PDF
Usando FastAPI
Autor: Asistente IA
Fecha: 2025
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import tempfile
import shutil
from pathlib import Path
import zipfile
import io
import uuid
from datetime import datetime

# Importar las clases del código original
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader

# Inicializar FastAPI
app = FastAPI(
    title="PDF Image Field API",
    description="API REST para agregar campos de imagen a archivos PDF",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para requests/responses
class ImageFieldConfig(BaseModel):
    field_name: str = "firma_empleado"
    x_pos: int = -27
    y_pos: int = 16
    width: int = 90
    height: int = 23

class ProcessResponse(BaseModel):
    success: bool
    message: str
    processed_files: int
    successful: int
    failed: int
    download_url: Optional[str] = None
    file_id: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    message: str
    timestamp: str

# Directorio temporal para archivos
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

# Clase principal (adaptada del código original)
class PDFImageFieldProcessor:
    def __init__(self, config: ImageFieldConfig):
        self.field_name = config.field_name
        self.x_pos = config.x_pos
        self.y_pos = config.y_pos
        self.width = config.width
        self.height = config.height
    
    def create_image_field_overlay(self, page_width=612, page_height=792):
        """Crea overlay con campo de imagen"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        
        # Ajustar posición
        adjusted_x = self.x_pos if self.x_pos >= 0 else page_width + self.x_pos
        adjusted_y = self.y_pos if self.y_pos >= 0 else page_height + self.y_pos
        
        # Crear campo de imagen
        c.acroForm.button(
            name=self.field_name,
            tooltip=f'Campo de imagen: {self.field_name}',
            x=adjusted_x,
            y=adjusted_y,
            width=self.width,
            height=self.height,
            borderStyle='inset',
            borderWidth=1,
            fillColor=white,
            borderColor=black,
            forceBorder=True
        )
        
        # Texto indicativo
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        text_x = adjusted_x + 5
        text_y = adjusted_y + (self.height/2) - 4
        c.drawString(text_x, text_y, "Imagen")
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def process_pdf(self, input_path: str, output_path: str) -> bool:
        """Procesa un PDF individual"""
        try:
            with open(input_path, 'rb') as file:
                reader = PdfReader(file)
                writer = PdfWriter()
                
                for page_num, page in enumerate(reader.pages):
                    page_rect = page.mediabox
                    page_width = float(page_rect.width)
                    page_height = float(page_rect.height)
                    
                    if page_num == 0:  # Solo primera página
                        overlay_buffer = self.create_image_field_overlay(page_width, page_height)
                        overlay_reader = PdfReader(overlay_buffer)
                        overlay_page = overlay_reader.pages[0]
                        page.merge_page(overlay_page)
                    
                    writer.add_page(page)
                
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            return True
        except Exception as e:
            print(f"Error procesando PDF: {e}")
            return False

# Endpoints de la API

@app.get("/", response_model=StatusResponse)
async def root():
    """Endpoint de estado de la API"""
    return StatusResponse(
        status="active",
        message="PDF Image Field API está funcionando correctamente",
        timestamp=datetime.now().isoformat()
    )

@app.get("/health", response_model=StatusResponse)
async def health_check():
    """Health check endpoint"""
    return StatusResponse(
        status="healthy",
        message="API operativa",
        timestamp=datetime.now().isoformat()
    )

@app.post("/process-single-pdf", response_model=ProcessResponse)
async def process_single_pdf(
    file: UploadFile = File(...),
    field_name: str = Form("firma_empleado"),
    x_pos: int = Form(-27),
    y_pos: int = Form(16),
    width: int = Form(90),
    height: int = Form(23)
):
    """
    Procesa un único archivo PDF y agrega campo de imagen
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    
    # Crear configuración
    config = ImageFieldConfig(
        field_name=field_name,
        x_pos=x_pos,
        y_pos=y_pos,
        width=width,
        height=height
    )
    
    # Generar ID único para el archivo
    file_id = str(uuid.uuid4())
    
    try:
        # Guardar archivo temporal
        input_path = TEMP_DIR / f"{file_id}_input.pdf"
        output_path = TEMP_DIR / f"{file_id}_output.pdf"
        
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Procesar PDF
        processor = PDFImageFieldProcessor(config)
        success = processor.process_pdf(str(input_path), str(output_path))
        
        if success:
            return ProcessResponse(
                success=True,
                message="PDF procesado exitosamente",
                processed_files=1,
                successful=1,
                failed=0,
                download_url=f"/download/{file_id}",
                file_id=file_id
            )
        else:
            raise HTTPException(status_code=500, detail="Error procesando el PDF")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    finally:
        # Limpiar archivo de entrada
        if input_path.exists():
            input_path.unlink()

@app.post("/process-multiple-pdfs", response_model=ProcessResponse)
async def process_multiple_pdfs(
    files: List[UploadFile] = File(...),
    field_name: str = Form("firma_empleado"),
    x_pos: int = Form(-27),
    y_pos: int = Form(16),
    width: int = Form(90),
    height: int = Form(23)
):
    """
    Procesa múltiples archivos PDF y los devuelve en un ZIP
    """
    if not files:
        raise HTTPException(status_code=400, detail="No se proporcionaron archivos")
    
    # Verificar que todos sean PDFs
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"Todos los archivos deben ser PDFs: {file.filename}")
    
    # Crear configuración
    config = ImageFieldConfig(
        field_name=field_name,
        x_pos=x_pos,
        y_pos=y_pos,
        width=width,
        height=height
    )
    
    # Generar ID único para el batch
    batch_id = str(uuid.uuid4())
    batch_dir = TEMP_DIR / f"batch_{batch_id}"
    batch_dir.mkdir()
    
    processor = PDFImageFieldProcessor(config)
    successful = 0
    failed = 0
    
    try:
        # Procesar cada archivo
        for file in files:
            try:
                input_path = batch_dir / f"input_{file.filename}"
                output_path = batch_dir / f"processed_{file.filename}"
                
                # Guardar archivo temporal
                with open(input_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # Procesar
                if processor.process_pdf(str(input_path), str(output_path)):
                    successful += 1
                else:
                    failed += 1
                
                # Limpiar entrada
                input_path.unlink()
                
            except Exception as e:
                print(f"Error procesando {file.filename}: {e}")
                failed += 1
        
        if successful > 0:
            # Crear ZIP con archivos procesados
            zip_path = TEMP_DIR / f"processed_pdfs_{batch_id}.zip"
            
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for processed_file in batch_dir.glob("processed_*"):
                    original_name = processed_file.name.replace("processed_", "")
                    zip_file.write(processed_file, original_name)
            
            return ProcessResponse(
                success=True,
                message=f"Procesados {successful} de {len(files)} archivos",
                processed_files=len(files),
                successful=successful,
                failed=failed,
                download_url=f"/download-zip/{batch_id}",
                file_id=batch_id
            )
        else:
            raise HTTPException(status_code=500, detail="No se pudo procesar ningún archivo")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    finally:
        # Limpiar directorio batch (excepto archivos finales)
        for file in batch_dir.glob("input_*"):
            if file.exists():
                file.unlink()

@app.get("/download/{file_id}")
async def download_processed_pdf(file_id: str):
    """
    Descarga un PDF procesado individual
    """
    file_path = TEMP_DIR / f"{file_id}_output.pdf"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=f"pdf_con_imagen_{file_id}.pdf",
        media_type="application/pdf"
    )

@app.get("/download-zip/{batch_id}")
async def download_processed_zip(batch_id: str):
    """
    Descarga ZIP con múltiples PDFs procesados
    """
    zip_path = TEMP_DIR / f"processed_pdfs_{batch_id}.zip"
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Archivo ZIP no encontrado")
    
    return FileResponse(
        path=zip_path,
        filename=f"pdfs_con_imagen_{batch_id}.zip",
        media_type="application/zip"
    )

@app.delete("/cleanup/{file_id}")
async def cleanup_files(file_id: str):
    """
    Limpia archivos temporales de un procesamiento específico
    """
    files_to_clean = [
        TEMP_DIR / f"{file_id}_output.pdf",
        TEMP_DIR / f"processed_pdfs_{file_id}.zip",
        TEMP_DIR / f"batch_{file_id}"
    ]
    
    cleaned = 0
    for file_path in files_to_clean:
        try:
            if file_path.is_file():
                file_path.unlink()
                cleaned += 1
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                cleaned += 1
        except Exception:
            pass
    
    return {"message": f"Limpiados {cleaned} elementos", "file_id": file_id}

@app.get("/config/default")
async def get_default_config():
    """
    Obtiene la configuración por defecto para campos de imagen
    """
    return {
        "field_name": "firma_empleado",
        "x_pos": -27,
        "y_pos": 16,
        "width": 90,
        "height": 23,
        "description": {
            "field_name": "Nombre del campo de imagen",
            "x_pos": "Posición X (-27 = 27 píxeles desde borde derecho)",
            "y_pos": "Posición Y desde abajo",
            "width": "Ancho del campo en píxeles",
            "height": "Alto del campo en píxeles"
        }
    }

# Cleanup automático al iniciar
@app.on_event("startup")
async def startup_event():
    """Limpiar archivos temporales al iniciar"""
    if TEMP_DIR.exists():
        for file in TEMP_DIR.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
            except Exception:
                pass
    print("🚀 API iniciada - Archivos temporales limpiados")

if __name__ == "__main__":
    import uvicorn
    print("🖼️  Iniciando API REST para campos de imagen en PDF")
    print("📡 Documentación disponible en: http://localhost:8000/docs")
    print("🔗 API disponible en: http://localhost:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
