import qrcode
import cv2
import uuid
import os
from database import Database
from PIL import Image
from datetime import datetime

class QRManager:
    
    def __init__(self):
        self.db = Database()
        os.makedirs("codigos_qr", exist_ok=True)
    
    def generar_qr(self, alumno_id, numero_control):
        """Genera un QR único para el alumno"""
        # Código único encriptado con datos del alumno
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
        
        # Guardar en BD
        self.db.ejecutar_query(
            "UPDATE alumnos SET codigo_qr=%s WHERE id=%s",
            (codigo_unico, alumno_id)
        )
        
        print(f"✅ QR generado: {codigo_unico}")
        return codigo_unico, path
    
    def leer_qr_camara(self):
        """Abre cámara para escanear QR"""
        cap = cv2.VideoCapture(0)
        detector = cv2.QRCodeDetector()
        
        print("📷 Escanee su código QR...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            data, bbox, _ = detector.detectAndDecode(frame)
            
            if data:
                # Verificar QR en BD
                alumno = self.db.obtener_datos(
                    "SELECT * FROM alumnos WHERE codigo_qr=%s AND activo=1",
                    (data,)
                )
                
                cap.release()
                cv2.destroyAllWindows()
                
                if alumno:
                    return alumno[0], data
                else:
                    print("❌ QR no válido o alumno inactivo")
                    return None, None
            
            cv2.putText(frame, "Coloque el QR frente a la camara", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Escanear QR - TECNM", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        return None, None