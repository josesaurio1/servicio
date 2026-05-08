import qrcode
import cv2
import uuid
import os
from database import Database
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm

class QRManager:
    
    def __init__(self):
        self.db = Database()
        os.makedirs("codigos_qr", exist_ok=True)
        os.makedirs("pdfs_qr", exist_ok=True)
    
    def generar_qr(self, alumno_id, numero_control):
        codigo_unico = f"TECNM-{numero_control}-{uuid.uuid4().hex[:8].upper()}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(codigo_unico)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        path = f"codigos_qr/QR_{numero_control}.png"
        img.save(path)
        self.db.ejecutar_query(
            "UPDATE alumnos SET codigo_qr=%s WHERE id=%s",
            (codigo_unico, alumno_id)
        )
        return codigo_unico, path
    
    def generar_pdf_qr(self, alumno_id, numero_control, nombre, apellidos, carrera, path_qr):
        """Genera un PDF con el código QR del alumno para que lo descargue"""
        pdf_path = f"pdfs_qr/QR_{numero_control}.pdf"
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        ancho, alto = letter
        
        # Fondo blanco con borde
        c.setStrokeColorRGB(0.1, 0.2, 0.5)
        c.setLineWidth(3)
        c.rect(1*cm, 1*cm, ancho - 2*cm, alto - 2*cm)
        
        # Encabezado TECNM
        c.setFillColorRGB(0.1, 0.2, 0.5)
        c.rect(1*cm, alto - 4*cm, ancho - 2*cm, 3*cm, fill=1)
        
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(ancho/2, alto - 2.2*cm, "TECNM - Control de Servicio Social")
        c.setFont("Helvetica", 12)
        c.drawCentredString(ancho/2, alto - 3.2*cm, "Credencial de Acceso - Código QR")
        
        # Datos del alumno
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(ancho/2, alto - 5.5*cm, f"{nombre} {apellidos}")
        
        c.setFont("Helvetica", 12)
        c.drawCentredString(ancho/2, alto - 6.5*cm, f"No. Control: {numero_control}")
        c.drawCentredString(ancho/2, alto - 7.3*cm, f"Carrera: {carrera}")
        c.drawCentredString(ancho/2, alto - 8.1*cm, f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y')}")
        
        # Imagen QR centrada
        qr_size = 8*cm
        x_qr = (ancho - qr_size) / 2
        y_qr = alto - 17*cm
        c.drawImage(path_qr, x_qr, y_qr, width=qr_size, height=qr_size)
        
        # Instrucciones
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawCentredString(ancho/2, y_qr - 1*cm, "Presenta este código QR al ingresar o salir")
        c.drawCentredString(ancho/2, y_qr - 1.6*cm, "No compartas este código con nadie")
        
        # Pie de página
        c.setFillColorRGB(0.1, 0.2, 0.5)
        c.rect(1*cm, 1*cm, ancho - 2*cm, 1.2*cm, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica", 9)
        c.drawCentredString(ancho/2, 1.5*cm, "Tecnológico Nacional de México — Documento oficial")
        
        c.save()
        print(f"✅ PDF generado: {pdf_path}")
        return pdf_path
    
    def leer_qr_camara(self):
        cap = cv2.VideoCapture(0)
        detector = cv2.QRCodeDetector()
        print("📷 Escanee su código QR...")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            data, bbox, _ = detector.detectAndDecode(frame)
            if data:
                alumno = self.db.obtener_datos(
                    "SELECT * FROM alumnos WHERE codigo_qr=%s AND activo=1", (data,)
                )
                cap.release()
                cv2.destroyAllWindows()
                if alumno:
                    return alumno[0], data
                else:
                    return None, None
            cv2.putText(frame, "Coloque el QR frente a la camara", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Escanear QR - TECNM", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        return None, None