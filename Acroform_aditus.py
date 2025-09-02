#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para agregar campos de firma (imagen) a archivos PDF existentes
Autor: Asistente IA
Fecha: 2025
"""

import os
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfform
from reportlab.lib.colors import black, white
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader
from reportlab.lib.units import inch
import tempfile
import io

class PDFSignatureFieldAdder:
    def __init__(self, field_name="firma_empleado", x_pos=-27, y_pos=16, width=90, height=23):
        """
        Inicializa el agregador de campos de firma
        
        Args:
            field_name (str): Nombre del campo de firma
            x_pos (int): Posición X del campo
            y_pos (int): Posición Y del campo
            width (int): Ancho del campo
            height (int): Alto del campo
        """
        self.field_name = field_name
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.width = width
        self.height = height
    
    def create_signature_field_overlay(self, page_width=612, page_height=792):
        """
        Crea un overlay PDF con el campo de firma
        
        Args:
            page_width (int): Ancho de la página
            page_height (int): Alto de la página
            
        Returns:
            io.BytesIO: Buffer con el PDF overlay
        """
        # Crear un buffer en memoria para el overlay
        buffer = io.BytesIO()
        
        # Crear canvas de reportlab
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        
        # Ajustar posición según el sistema de coordenadas de PDF
        # PDF usa coordenadas desde abajo-izquierda
        adjusted_x = self.x_pos if self.x_pos >= 0 else page_width + self.x_pos
        adjusted_y = self.y_pos if self.y_pos >= 0 else page_height + self.y_pos
        
        # Crear el campo de imagen/firma
        c.acroForm.textfield(
            name=self.field_name,
            tooltip=f'Campo de firma: {self.field_name}',
            x=adjusted_x,
            y=adjusted_y,
            borderStyle='inset',
            borderWidth=1,
            width=self.width,
            height=self.height,
            textColor=black,
            fillColor=white,
            borderColor=black,
            forceBorder=True
        )
        
        # Finalizar el canvas
        c.save()
        
        # Resetear el buffer para lectura
        buffer.seek(0)
        return buffer
    
    def add_signature_field_to_pdf(self, input_path, output_path=None):
        """
        Agrega campo de firma a un archivo PDF específico
        
        Args:
            input_path (str): Ruta del archivo PDF de entrada
            output_path (str): Ruta del archivo PDF de salida (opcional)
            
        Returns:
            bool: True si fue exitoso, False en caso contrario
        """
        try:
            # Definir ruta de salida si no se proporciona
            if output_path is None:
                path_obj = Path(input_path)
                output_path = path_obj.parent / f"{path_obj.stem}_con_firma{path_obj.suffix}"
            
            # Leer el PDF original
            with open(input_path, 'rb') as file:
                reader = PdfReader(file)
                writer = PdfWriter()
                
                # Procesar cada página
                for page_num, page in enumerate(reader.pages):
                    # Obtener dimensiones de la página
                    page_rect = page.mediabox
                    page_width = float(page_rect.width)
                    page_height = float(page_rect.height)
                    
                    # Crear overlay con campo de firma solo en la primera página
                    if page_num == 0:
                        overlay_buffer = self.create_signature_field_overlay(page_width, page_height)
                        overlay_reader = PdfReader(overlay_buffer)
                        overlay_page = overlay_reader.pages[0]
                        
                        # Combinar la página original con el overlay
                        page.merge_page(overlay_page)
                    
                    # Agregar página al writer
                    writer.add_page(page)
                
                # Guardar el archivo modificado
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            print(f"✓ Campo de firma agregado exitosamente a: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error procesando {input_path}: {str(e)}")
            return False
    
    def process_multiple_pdfs(self, input_directory, output_directory=None, file_pattern="*.pdf"):
        """
        Procesa múltiples archivos PDF en un directorio
        
        Args:
            input_directory (str): Directorio con archivos PDF de entrada
            output_directory (str): Directorio para archivos de salida (opcional)
            file_pattern (str): Patrón de archivos a procesar
            
        Returns:
            dict: Estadísticas del procesamiento
        """
        input_path = Path(input_directory)
        
        if not input_path.exists():
            print(f"✗ El directorio {input_directory} no existe")
            return {"procesados": 0, "exitosos": 0, "fallidos": 0}
        
        # Definir directorio de salida
        if output_directory is None:
            output_path = input_path / "pdfs_con_firma"
        else:
            output_path = Path(output_directory)
        
        # Crear directorio de salida si no existe
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Encontrar archivos PDF
        pdf_files = list(input_path.glob(file_pattern))
        
        if not pdf_files:
            print(f"✗ No se encontraron archivos PDF en {input_directory}")
            return {"procesados": 0, "exitosos": 0, "fallidos": 0}
        
        print(f"📁 Encontrados {len(pdf_files)} archivos PDF para procesar")
        print(f"📂 Directorio de salida: {output_path}")
        print("-" * 50)
        
        # Contadores
        exitosos = 0
        fallidos = 0
        
        # Procesar cada archivo
        for pdf_file in pdf_files:
            output_file = output_path / f"{pdf_file.stem}_con_firma{pdf_file.suffix}"
            
            if self.add_signature_field_to_pdf(str(pdf_file), str(output_file)):
                exitosos += 1
            else:
                fallidos += 1
        
        # Mostrar estadísticas
        print("-" * 50)
        print(f"📊 Procesamiento completado:")
        print(f"   • Archivos procesados: {len(pdf_files)}")
        print(f"   • Exitosos: {exitosos}")
        print(f"   • Fallidos: {fallidos}")
        
        return {
            "procesados": len(pdf_files),
            "exitosos": exitosos,
            "fallidos": fallidos
        }

def main():
    """Función principal del script"""
    print("🔄 Iniciando procesador de campos de firma PDF")
    print("=" * 50)
    
    # Crear instancia del procesador con los parámetros especificados
    processor = PDFSignatureFieldAdder(
        field_name="firma_empleado",
        x_pos=-27,  # 27 píxeles desde el borde derecho
        y_pos=16,   # 16 píxeles desde abajo
        width=90,   # 90 píxeles de ancho
        height=23   # 23 píxeles de alto
    )
    
    # Ejemplo de uso: procesar un directorio
    input_dir = input("📁 Ingresa la ruta del directorio con archivos PDF: ").strip()
    
    if not input_dir:
        # Usar directorio actual si no se proporciona ruta
        input_dir = "."
        print("📂 Usando directorio actual")
    
    # Procesar archivos
    stats = processor.process_multiple_pdfs(input_dir)
    
    if stats["exitosos"] > 0:
        print("✅ Procesamiento completado exitosamente")
    else:
        print("❌ No se procesaron archivos exitosamente")

# Función de utilidad para uso individual
def add_signature_to_single_pdf(input_file, output_file=None):
    """
    Función de conveniencia para agregar firma a un solo PDF
    
    Args:
        input_file (str): Ruta del archivo PDF de entrada
        output_file (str): Ruta del archivo PDF de salida (opcional)
    
    Returns:
        bool: True si fue exitoso
    """
    processor = PDFSignatureFieldAdder(
        field_name="firma_empleado",
        x_pos=-27,
        y_pos=16,
        width=90,
        height=23
    )
    
    return processor.add_signature_field_to_pdf(input_file, output_file)

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import PyPDF2
        import reportlab
    except ImportError as e:
        print("❌ Error: Faltan dependencias requeridas")
        print("💡 Instala las dependencias con:")
        print("   pip install PyPDF2 reportlab")
        sys.exit(1)
    
    main()